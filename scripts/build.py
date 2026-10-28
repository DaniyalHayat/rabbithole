from __future__ import annotations
import gzip, hashlib, json, math, sqlite3, sys, time
from collections import Counter
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from rabbithole.search import SearchIndex
from rabbithole.graph import pagerank, components
from rabbithole.geo import research_geojson, affiliation_counts

def reconstruct(index):
    if not isinstance(index, dict):
        return ''
    positions = [(p, word) for word, offsets in index.items() for p in offsets if isinstance(p, int) and p >= 0]
    return ' '.join(w for _, w in sorted(positions))

def clean_work(w):
    wid = str(w.get('id', '')).rsplit('/', 1)[-1]
    if not wid.startswith('W') or not wid[1:].isdigit() or not str(w.get('title') or '').strip():
        raise ValueError('missing/invalid id or title')
    year = w.get('publication_year')
    if year is not None and not 1600 <= year <= 2026:
        raise ValueError('invalid publication year')
    topics = [{'id': t['id'].rsplit('/', 1)[-1], 'name': t['display_name']} for t in w.get('topics', []) if t.get('id') and t.get('display_name')]
    return {'id': wid, 'title': w['title'].strip(), 'year': year, 'doi': w.get('doi'), 'type': w.get('type') or 'unknown', 'cited': max(int(w.get('cited_by_count') or 0), 0), 'oa': bool((w.get('open_access') or {}).get('is_oa')), 'oa_url': (w.get('open_access') or {}).get('oa_url'), 'retracted': bool(w.get('is_retracted')), 'abstract': reconstruct(w.get('abstract_inverted_index')), 'topics': topics, 'authors': [a.get('author', {}).get('display_name', '') for a in w.get('authorships', [])[:3]], 'references': sorted(set(x.rsplit('/', 1)[-1] for x in w.get('referenced_works', []) if x.rsplit('/',1)[-1] != wid)), 'themes': []}

def main():
    start = time.perf_counter()
    raw = ROOT / 'data/raw'
    manifest = json.loads((raw / 'manifest.json').read_text(encoding='utf-8'))
    snapshot = None
    if not all((raw / e['file']).exists() for e in manifest['files']):
        archive = ROOT / 'data/openalex_snapshot.json.gz'
        expected = (ROOT / 'data/snapshot_checksum.txt').read_text().split()[0]
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ValueError('Locked source archive checksum mismatch')
        snapshot = json.loads(gzip.decompress(archive.read_bytes()))
        if snapshot['manifest'] != manifest:
            raise ValueError('Source archive and manifest disagree')
    papers, quarantine, provenance = {}, [], []
    for item in manifest['files']:
        path = raw / item['file']
        if snapshot is None:
            if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Snapshot checksum mismatch: ' + path.name)
            source = json.loads(path.read_text(encoding='utf-8'))
        else:
            source = snapshot['files'][item['file']]
        for w in source['results']:
            try:
                paper = clean_work(w)
            except (ValueError, TypeError, KeyError) as e:
                quarantine.append({'file':path.name,'id':w.get('id'),'reason':str(e)})
                continue
            paper['countries'] = sorted({country for a in w.get('authorships', []) for country in a.get('countries', []) if isinstance(country,str) and len(country)==2 and country.isalpha()})
            key = paper['id']
            if key not in papers:
                papers[key] = paper
            elif not papers[key]['abstract'] and paper['abstract']:
                papers[key]['abstract'] = paper['abstract']
            if item['theme'] not in papers[key]['themes']:
                papers[key]['themes'].append(item['theme'])
            provenance.append((key, path.name, item['theme']))
    docs = sorted(papers.values(), key=lambda p:p['id'])
    lookup = {p['id']: i for i,p in enumerate(docs)}
    edges = sorted(set((lookup[p['id']],lookup[r]) for p in docs for r in p['references'] if r in lookup))
    rank = pagerank(len(docs), edges)
    index_docs = [{'id':p['id'],'title':p['title'],'text':p['title']+' '+p['title']+' '+p['abstract']+' '+' '.join(t['name'] for t in p['topics'])} for p in docs]
    index = SearchIndex(index_docs)
    processed = ROOT / 'data/processed'
    processed.mkdir(exist_ok=True)
    dbpath = processed / 'research.sqlite'
    # A new temporary database makes a failed rebuild leave the last valid one intact.
    temp = processed / 'research.next.sqlite'
    if temp.exists():
        temp.unlink()
    with sqlite3.connect(temp) as db:
        db.executescript((ROOT / 'sql/schema.sql').read_text())
        for p in docs:
            db.execute('INSERT INTO papers VALUES(?,?,?,?,?,?,?,?,?)',(p['id'],p['title'],p['year'],p['doi'],p['abstract'],p['type'],int(p['oa']),int(p['retracted']),p['cited']))
            db.execute('INSERT INTO paper_search VALUES(?,?,?)',(p['id'],p['title'],p['abstract']))
            db.executemany('INSERT OR IGNORE INTO paper_countries VALUES(?,?)',[(p['id'],c) for c in p['countries']])
            for t in p['topics']:
                db.execute('INSERT OR IGNORE INTO topics VALUES(?,?)',(t['id'],t['name']))
                db.execute('INSERT OR IGNORE INTO paper_topics VALUES(?,?)',(p['id'],t['id']))
        db.executemany('INSERT INTO citations VALUES(?,?)',[(docs[a]['id'],docs[b]['id']) for a,b in edges])
        db.executemany('INSERT INTO provenance VALUES(?,?,?)',provenance)
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    db.close()
    temp.replace(dbpath)
    for i,p in enumerate(docs):
        p['references'] = [r for r in p['references'] if r in lookup]
        p['rank'] = round(float(rank[i]), 8)
        p['vector'] = np.round(index.embeddings[i], 5).tolist()
    stats = {'papers':len(docs), 'source_rows':sum(x['rows'] for x in manifest['files']), 'duplicates_merged':sum(x['rows'] for x in manifest['files'])-len(docs)-len(quarantine), 'citation_edges':len(edges),'topics':len({t['id'] for p in docs for t in p['topics']}),'abstracts':sum(bool(p['abstract']) for p in docs),'open_access':sum(p['oa'] for p in docs),'retracted':sum(p['retracted'] for p in docs),'quarantined':len(quarantine),'components':len(components(len(docs),edges)),'largest_component':len(components(len(docs),edges)[0]),'themes':dict(Counter(t for p in docs for t in p['themes'])),'snapshot':manifest['retrieved_at'],'build_seconds':round(time.perf_counter()-start,3)}
    bundle = {'papers':docs,'edges':edges,'stats':stats,'search':{'vocab':index.vocab,'idf':np.round(index.idf,5).tolist(),'basis':np.round(index.basis,5).tolist(),'dimensions':int(index.basis.shape[1]),'weight':.15}}
    boundary_path=ROOT / 'data/natural_earth_countries.geojson'
    if (ROOT / 'data/geo_manifest.json').exists():
        geo_manifest=json.loads((ROOT / 'data/geo_manifest.json').read_text())
        if hashlib.sha256(boundary_path.read_bytes()).hexdigest()!=geo_manifest['sha256']:
            raise ValueError('Boundary source checksum mismatch')
    boundaries = json.loads(boundary_path.read_text(encoding='utf-8'))
    bundle['geography'] = research_geojson(docs,boundaries)
    bundle['stats']['countries'] = len(affiliation_counts(docs))
    bundle['stats']['papers_with_country'] = sum(bool(p['countries']) for p in docs if not p['retracted'])
    (ROOT / 'outputs/research_atlas.geojson').write_text(json.dumps(bundle['geography'],ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    if (ROOT / 'outputs/ml_model.json').exists():
        bundle['ml_model'] = json.loads((ROOT / 'outputs/ml_model.json').read_text())
        bundle['ml_benchmark'] = json.loads((ROOT / 'outputs/ml_benchmark.json').read_text())
    if (ROOT / 'outputs/benchmark.json').exists():
        bundle['benchmark'] = json.loads((ROOT / 'outputs/benchmark.json').read_text())
    (processed / 'corpus.json').write_text(json.dumps(bundle,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    # Script data works offline in both file:// and Figma without an API server.
    (ROOT / 'app/data.js').write_text('window.RH_DATA='+json.dumps(bundle,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n',encoding='utf-8')
    (ROOT / 'outputs/build_report.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    (ROOT / 'outputs/quarantine.json').write_text(json.dumps(quarantine,indent=2),encoding='utf-8')
    import csv
    with (ROOT/'outputs/pagerank_reference.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f); writer.writerow(['id','pagerank']);writer.writerows((p['id'],format(rank[i],'.15g')) for i,p in enumerate(docs))
    with (ROOT/'outputs/citation_edges.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f); writer.writerow(['source','target']);writer.writerows((docs[a]['id'],docs[b]['id']) for a,b in edges)
    print(json.dumps(stats,indent=2))

if __name__ == '__main__':
    main()
