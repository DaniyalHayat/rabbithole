"""Select fusion weight on BEIR train judgments, then evaluate the untouched test split."""
from __future__ import annotations
import csv, json, math, sys, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rabbithole.search import SearchIndex

def metrics(ranked, relevant, k=10):
    ranked=ranked[:k]
    gains=[int(x in relevant) for x in ranked]
    dcg=sum(g/math.log2(i+2) for i,g in enumerate(gains))
    ideal=sum(1/math.log2(i+2) for i in range(min(len(relevant),k)))
    return {'ndcg10':dcg/ideal if ideal else 0.,'recall10':sum(gains)/len(relevant) if relevant else 0.,'mrr10':next((1/(i+1) for i,g in enumerate(gains) if g),0.)}

def read_qrels(path):
    result={}
    with path.open(encoding='utf-8') as f:
        for row in csv.DictReader(f,delimiter='\t'):
            if int(row['score'])>0:
                result.setdefault(row['query-id'],set()).add(row['corpus-id'])
    return result

def main():
    raw=ROOT/'data/raw/scifact'
    docs=[json.loads(line) for line in (raw/'corpus.jsonl').read_text(encoding='utf-8').splitlines()]
    queries={x['_id']:x['text'] for x in map(json.loads,(raw/'queries.jsonl').read_text(encoding='utf-8').splitlines())}
    train=read_qrels(raw/'qrels/train.tsv'); test=read_qrels(raw/'qrels/test.tsv')
    assert not (set(train)&set(test)), 'Query split overlap'
    index=SearchIndex([{'id':d['_id'],'title':d['title'],'text':d['title']+' '+d['title']+' '+d['text']} for d in docs])
    ids=[d['_id'] for d in docs]
    def evaluate(qrels,weight):
        rows=[]
        for qid,relevant in sorted(qrels.items()):
            started=time.perf_counter()
            ranked=[ids[i] for i,_ in index.rank(queries[qid],weight=weight,limit=10)]
            row={'query_id':qid,**metrics(ranked,relevant),'milliseconds':(time.perf_counter()-started)*1000}
            rows.append(row)
        return rows
    dev=[]
    for weight in [0.,.1,.15,.25,.4]:
        rows=evaluate(train,weight)
        dev.append({'weight':weight,'ndcg10':float(np.mean([x['ndcg10'] for x in rows]))})
    selected=max(dev,key=lambda r:(r['ndcg10'],-r['weight']))['weight']
    # No test-query labels are used above this point.
    baseline=evaluate(test,0.); hybrid=evaluate(test,selected)
    rng=np.random.default_rng(42)
    delta=np.array([b['ndcg10']-a['ndcg10'] for a,b in zip(baseline,hybrid)])
    boot=rng.choice(delta,size=(5000,len(delta)),replace=True).mean(axis=1)
    report={'dataset':'BEIR SciFact','documents':len(docs),'train_queries':len(train),'test_queries':len(test),'latent_dimensions':index.embeddings.shape[1],'selection':'Fusion weight chosen only on official train judgments; fixed corpus used for unsupervised LSA. No graph reranking in this benchmark.','selected_weight':selected,'development':dev,'baseline':{k:float(np.mean([r[k] for r in baseline])) for k in ['ndcg10','recall10','mrr10']},'selected':{k:float(np.mean([r[k] for r in hybrid])) for k in ['ndcg10','recall10','mrr10']},'ndcg10_difference':float(delta.mean()),'paired_bootstrap_95_ci':np.quantile(boot,[.025,.975]).tolist(),'bootstrap_resamples':5000,'seed':42,'latency_ms':{'median':float(np.median([r['milliseconds'] for r in hybrid])),'p95':float(np.quantile([r['milliseconds'] for r in hybrid],.95))},'scope':'Biomedical abstract retrieval is an external engineering benchmark. These scores do not establish relevance on the curiosity corpus, factual accuracy, or user learning outcomes.'}
    (ROOT/'outputs/benchmark.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (ROOT/'outputs/query_metrics.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['query_id','bm25_ndcg10','selected_ndcg10','difference'])
        writer.writerows((a['query_id'],a['ndcg10'],b['ndcg10'],b['ndcg10']-a['ndcg10']) for a,b in zip(baseline,hybrid))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
