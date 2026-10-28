import json, math, sqlite3, sys, unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from rabbithole.search import SearchIndex, tokenize, mmr
from rabbithole.graph import pagerank, shortest_path, components
from build import reconstruct, clean_work
from benchmark import metrics

class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=SearchIndex([{'id':'a','title':'music memory','text':'music memory music emotion'},{'id':'b','title':'sleep memory','text':'sleep dreams memory dreams'},{'id':'c','title':'green nature','text':'green nature nature park'}],dimensions=2)
    def test_tokenization(self):self.assertEqual(tokenize('Why is MUSIC, in 2024?'),['music','2024'])
    def test_keyword_relevance(self):self.assertEqual(self.index.rank('music')[0][0],0)
    def test_empty_query(self):self.assertEqual(self.index.rank('the and'),[])
    def test_unknown_query(self):self.assertEqual(self.index.rank('zzzzzz'),[])
    def test_scores_finite(self):self.assertTrue(np.isfinite(self.index.scores('music memory')).all())
    def test_semantic_vectors_normalized_or_zero(self):
        lengths=np.linalg.norm(self.index.embeddings,axis=1)
        self.assertTrue(np.all(np.isclose(lengths,1)|np.isclose(lengths,0)))
    def test_no_duplicates(self):self.assertEqual(len({i for i,_ in self.index.rank('memory')}),len(self.index.rank('memory')))
    def test_determinism(self):self.assertEqual(self.index.rank('dreams'),self.index.rank('dreams'))
    def test_empty_corpus(self):self.assertRaises(ValueError,SearchIndex,[])
    def test_mmr_uniqueness(self):self.assertEqual(len(set(mmr([0,1,2],[1,.9,.8],self.index.embeddings,3))),3)

class GraphTests(unittest.TestCase):
    def test_cycle_uniform(self):self.assertTrue(np.allclose(pagerank(3,[(0,1),(1,2),(2,0)]),[1/3]*3))
    def test_dangling_mass_conservation(self):self.assertAlmostEqual(pagerank(3,[(0,1)]).sum(),1.)
    def test_empty_graph_uniform(self):self.assertTrue(np.allclose(pagerank(4,[]),[.25]*4))
    def test_personalized_rank(self):self.assertGreater(pagerank(3,[],personalization=[1,0,0])[0],.99)
    def test_invalid_edges_rejected(self):self.assertRaises(ValueError,pagerank,3,[(0,5)])
    def test_invalid_prior_rejected(self):self.assertRaises(ValueError,pagerank,3,[],personalization=[0,0,0])
    def test_shortest_citation_path(self):self.assertEqual(shortest_path(0,3,[(0,1),(1,2),(2,3)]),[0,1,2,3])
    def test_disconnected_path(self):self.assertEqual(shortest_path(0,4,[(0,1),(3,4)]),[])
    def test_components(self):self.assertEqual(sorted(map(len,components(5,[(0,1),(1,2)]))),[1,1,3])

class DataTests(unittest.TestCase):
    def test_abstract_order(self):self.assertEqual(reconstruct({'world':[1],'hello':[0,2]}),'hello world hello')
    def test_missing_abstract(self):self.assertEqual(reconstruct(None),'')
    def test_bad_work_quarantined(self):self.assertRaises(ValueError,clean_work,{'id':'bad','title':'Title'})
    def test_missing_title_rejected(self):self.assertRaises(ValueError,clean_work,{'id':'https://openalex.org/W123','title':None})
    def test_bad_year_rejected(self):self.assertRaises(ValueError,clean_work,{'id':'https://openalex.org/W123','title':'A','publication_year':3000})
    def test_database_constraints(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript((ROOT/'sql/schema.sql').read_text())
            with self.assertRaises(sqlite3.IntegrityError):db.execute('INSERT INTO citations VALUES(?,?)',('missing','other'))
    def test_actual_graph_integrity(self):
        d=json.loads((ROOT/'data/processed/corpus.json').read_text(encoding='utf-8'))
        self.assertEqual(len({p['id'] for p in d['papers']}),len(d['papers']))
        self.assertTrue(all(0<=a<len(d['papers']) and 0<=b<len(d['papers']) and a!=b for a,b in d['edges']))
        self.assertEqual(len(d['edges']),len(set(map(tuple,d['edges']))))
        with sqlite3.connect(ROOT/'data/processed/research.sqlite') as db:
            self.assertFalse(db.execute('PRAGMA foreign_key_check').fetchall())
            self.assertEqual(db.execute('SELECT count(*) FROM papers').fetchone()[0],len(d['papers']))
    def test_perfect_ndcg(self):self.assertEqual(metrics(['x','y'],{'x'})['ndcg10'],1.)
    def test_reciprocal_rank(self):self.assertEqual(metrics(['a','b','c'],{'b'})['mrr10'],.5)
    def test_recall(self):self.assertEqual(metrics(['a'],{'a','b'})['recall10'],.5)
    def test_empty_metrics(self):self.assertEqual(metrics([],set()),{'ndcg10':0.,'recall10':0.,'mrr10':0.})

if __name__=='__main__':unittest.main()
