import json, sys, unittest
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rabbithole.search import SearchIndex
from rabbithole.ranker import features, predict
data=json.loads((ROOT/'data/processed/corpus.json').read_text(encoding='utf-8'))
index=SearchIndex([{'id':p['id'],'title':p['title'],'text':p['title']+' '+p['title']+' '+p['abstract']+' '+' '.join(t['name'] for t in p['topics'])} for p in data['papers']])
cases=[]
for q in ['music memory emotion','dreaming sleep memory','attention distraction','loneliness social connection','curiosity learning','habit formation','awe nature wellbeing','time perception']:
    ranked=[(i,s) for i,s in index.rank(q,limit=30) if not data['papers'][i]['retracted']][:10]
    case={'query':q,'ids':[data['papers'][i]['id'] for i,_ in ranked],'scores':[s for _,s in ranked]}
    if data.get('ml_model'):
        x=features(index,q);base=.85*x[:,0]+.15*x[:,1]
        candidates=[int(i) for i in np.argsort(-base,kind='stable') if not data['papers'][i]['retracted']][:50]
        scores={i:float(s) for i,s in zip(candidates,predict(data['ml_model'],x[candidates]))}
        ml=sorted(candidates,key=lambda i:(-scores[i],i))[:10]
        case.update({'ml_ids':[data['papers'][i]['id'] for i in ml],'ml_scores':[scores[i] for i in ml]})
    cases.append(case)
(ROOT/'outputs/search_parity.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
(ROOT/'outputs/python_test_report.json').write_text(json.dumps({'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors),'failures':len(result.failures),'errors':len(result.errors)},indent=2),encoding='utf-8')
sys.exit(0 if result.wasSuccessful() else 1)
