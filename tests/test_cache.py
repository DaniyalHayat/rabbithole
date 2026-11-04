import math
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import fakeredis
from rabbithole.cache import SearchCache
from rabbithole.search import SearchIndex, tokenize


class CacheTests(unittest.TestCase):
    def test_redis_hit_expiry_and_corpus_isolation(self):
        redis = fakeredis.FakeRedis()
        cache = SearchCache('a', client=redis)
        calls = []
        def compute():
            calls.append(1)
            return {'ids':['one']}
        self.assertEqual(cache.get_or_compute({'q':'music'}, compute)[1], 'redis-miss')
        self.assertEqual(cache.get_or_compute({'q':'music'}, compute)[1], 'redis-hit')
        self.assertEqual(len(calls), 1)
        key = redis.keys()[0]
        self.assertGreater(redis.ttl(key), 0)
        redis.delete(key)
        self.assertEqual(cache.get_or_compute({'q':'music'}, compute)[1], 'redis-miss')
        self.assertEqual(SearchCache('b', client=redis).get_or_compute({'q':'music'}, compute)[1], 'redis-miss')

    def test_connection_failure_does_not_break_search(self):
        import redis
        class Offline:
            def get(self, key): raise redis.ConnectionError('offline')
            def set(self, *a, **kw): raise redis.ConnectionError('offline')
        self.assertEqual(SearchCache('a', client=Offline()).get_or_compute({}, lambda: [1]), ([1], 'uncached'))

    def test_sparse_bm25_matches_independent_dense_equation(self):
        index=SearchIndex([{'title':str(i),'text':text} for i,text in enumerate(['music memory music','sleep memory dreams','nature park'])], dimensions=2)
        dense=np.zeros(index.n)
        for term in set(tokenize('music memory')):
            df=index.df.get(term,0)
            if not df: continue
            idf=math.log(1+(index.n-df+.5)/(df+.5))
            for i,row in enumerate(index.counts):
                tf=row.get(term,0)
                dense[i]+=idf*tf*2.2/(tf+1.2*(.25+.75*index.lengths[i]/index.avgdl))
        np.testing.assert_allclose(index.bm25('music memory'), dense, atol=1e-12)
