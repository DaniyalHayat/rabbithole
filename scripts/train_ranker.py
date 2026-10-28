"""Train pairwise logistic ranking on SciFact train only; evaluate final test once."""
import csv, hashlib, json, sys, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from rabbithole.search import SearchIndex
from rabbithole.ranker import features, fit_pairwise, predict
from benchmark import read_qrels, metrics

def main():
    raw=ROOT/'data/raw/scifact'
    docs=list(map(json.loads,(raw/'corpus.jsonl').read_text(encoding='utf8').splitlines()))
    queries={x['_id']:x['text'] for x in map(json.loads,(raw/'queries.jsonl').read_text(encoding='utf8').splitlines())}
    train=read_qrels(raw/'qrels/train.tsv');test=read_qrels(raw/'qrels/test.tsv')
    assert not set(train)&set(test)
    # Identical query texts stay in one development partition.
    # Only official train labels choose model parameters. Official test labels are used below, after fitting.
    heldout={qid for qid in train if int(hashlib.sha256(queries[qid].lower().encode()).hexdigest(),16)%5==0}
    fit_ids=set(train)-heldout
    index=SearchIndex([{'id':d['_id'],'title':d['title'],'text':d['title']+' '+d['title']+' '+d['text']} for d in docs])
    ids=[d['_id'] for d in docs];lookup={x:i for i,x in enumerate(ids)}
    cache={}
    for qid in sorted(set(train)|set(test)):
        x=features(index,queries[qid]);base=.85*x[:,0]+.15*x[:,1]
        candidates=np.argsort(-base,kind='stable')[:50]
        # Store full feature rows for labeled positives as well as the fixed candidate pool.
        cache[qid]=(x,candidates,base)
    def pairs(qids):
        result=[]
        for qid in sorted(qids):
            x,candidates,_=cache[qid]
            negatives=[i for i in candidates if ids[i] not in train[qid]][:15]
            for positive in sorted(train[qid]):
                result.extend(x[lookup[positive]]-x[i] for i in negatives)
        return np.array(result)
    def evaluate(qids,model,qrels):
        rows=[]
        for qid in sorted(qids):
            x,candidates,base=cache[qid]
            ranked=candidates[np.argsort(-predict(model,x[candidates]),kind='stable')]
            rows.append({'query_id':qid,**metrics([ids[i] for i in ranked],qrels[qid]),'baseline':metrics([ids[i] for i in np.argsort(-base,kind='stable')[:10]],qrels[qid])})
        return rows
    candidates=[]
    fit_pairs=pairs(fit_ids)
    for l2 in [.001,.01,.1]:
        model=fit_pairwise(fit_pairs,l2=l2)
        rows=evaluate(heldout,model,train)
        candidates.append({'l2':l2,'development_ndcg10':float(np.mean([r['ndcg10'] for r in rows]))})
    chosen=max(candidates,key=lambda x:(x['development_ndcg10'],x['l2']))['l2']
    all_pairs=pairs(set(train));model=fit_pairwise(all_pairs,l2=chosen)
    model.update({'training_dataset':'BEIR SciFact official train','training_queries':len(train),'training_pairs':len(all_pairs),'candidate_pool':50,'negative_policy':'Top 15 unjudged/nonrelevant hybrid candidates per labeled positive; unjudged is an assumption, not verified nonrelevance.','scope':'Experimental cross-domain transfer to curiosity papers; scores are ranking utilities, not calibrated relevance probabilities.'})
    rows=evaluate(set(test),model,test)
    delta=np.array([r['ndcg10']-r['baseline']['ndcg10'] for r in rows]);rng=np.random.default_rng(42)
    boot=rng.choice(delta,size=(5000,len(delta)),replace=True).mean(axis=1)
    report={'dataset':'BEIR SciFact','documents':len(docs),'training_queries':len(train),'development_queries':len(heldout),'fitting_queries':len(fit_ids),'test_queries':len(test),'training_pairs':len(all_pairs),'regularization_search':candidates,'selected_l2':chosen,'metrics':{k:float(np.mean([r[k] for r in rows])) for k in ['ndcg10','recall10','mrr10']},'hybrid_baseline':{k:float(np.mean([r['baseline'][k] for r in rows])) for k in ['ndcg10','recall10','mrr10']},'paired_ndcg_difference':float(delta.mean()),'paired_bootstrap_95_ci':np.quantile(boot,[.025,.975]).tolist(),'bootstrap_resamples':5000,'seed':42,'scope':model['scope'],'development_split':'Deterministic query-text hash within official train; near-duplicate semantic claims may cross partitions. No official test labels select model or regularization.'}
    (ROOT/'outputs/ml_model.json').write_text(json.dumps(model,indent=2))
    (ROOT/'outputs/ml_benchmark.json').write_text(json.dumps(report,indent=2))
    with (ROOT/'outputs/ml_query_metrics.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['query_id','hybrid_ndcg10','ml_ndcg10','difference']);writer.writerows((r['query_id'],r['baseline']['ndcg10'],r['ndcg10'],r['ndcg10']-r['baseline']['ndcg10']) for r in rows)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
