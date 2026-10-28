"""Static app + read-only local API. Bind locally; no account, secrets or LLM needed."""
from __future__ import annotations
import argparse, json, sqlite3, sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from rabbithole.search import SearchIndex, tokenize

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    bundle=json.loads((ROOT/'data/processed/corpus.json').read_text(encoding='utf-8')) if (ROOT/'data/processed/corpus.json').exists() else None
    index=SearchIndex([{'id':p['id'],'title':p['title'],'text':p['title']+' '+p['title']+' '+p['abstract']+' '+' '.join(t['name'] for t in p['topics'])} for p in bundle['papers']]) if bundle else None
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            url=urlsplit(self.path)
            if url.path.startswith('/api/'):
                if not bundle:
                    self.send_json({'error':'Run python run.py to enable the API; the browser app already works.'},503);return
                query=parse_qs(url.query).get('q',[''])[0][:500]
                if url.path=='/api/health':self.send_json({'status':'ok',**bundle['stats']});return
                if url.path=='/api/search':
                    result=[{**bundle['papers'][i],'score':score} for i,score in index.rank(query,limit=40) if not bundle['papers'][i]['retracted']][:20]
                    self.send_json({'results':result,'query':query});return
                if url.path=='/api/fts':
                    safe=' OR '.join('"'+t+'"' for t in tokenize(query))
                    with sqlite3.connect('file:'+str(ROOT/'data/processed/research.sqlite')+'?mode=ro',uri=True) as db:
                        rows=db.execute('SELECT paper_search.id,paper_search.title,bm25(paper_search) FROM paper_search JOIN papers p ON p.id=paper_search.id WHERE paper_search MATCH ? AND p.retracted=0 ORDER BY bm25(paper_search) LIMIT 20',(safe,)).fetchall() if safe else []
                    db.close()
                    self.send_json({'results':rows});return
                self.send_json({'error':'Unknown endpoint'},404);return
            return super().do_GET()
        def send_json(self,obj,status=200):
            payload=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(ROOT/'app')))
    print(f'RabbitHole: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()

if __name__=='__main__':main()
