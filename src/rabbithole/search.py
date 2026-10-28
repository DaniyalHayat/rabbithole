"""Sparse BM25 + randomized LSA, without a model service or opaque API."""
from __future__ import annotations
from collections import Counter
import math, re
import numpy as np

STOP = set('a an and are as at be been but by can could did do does for from had has have how i if in into is it its may more most not of on or our should so some than that the their there these they this those to was we were what when where which who why will with would you your'.split())

def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", str(text).lower()) if len(t) > 1 and t not in STOP]

def normalize(x):
    x = np.asarray(x, dtype=float)
    return x / max(float(np.linalg.norm(x)), 1e-12)

class SearchIndex:
    def __init__(self, docs, dimensions=48, seed=42):
        if not docs:
            raise ValueError('At least one document is required')
        self.docs = docs
        self.counts = [Counter(tokenize(d.get('text', d['title']))) for d in docs]
        self.df = Counter()
        for row in self.counts:
            self.df.update(row.keys())
        self.n = len(docs)
        self.lengths = np.array([sum(c.values()) for c in self.counts], dtype=float)
        self.avgdl = max(float(self.lengths.mean()), 1.)
        self.vocab = sorted(t for t, n in self.df.items() if n >= 2)
        self.term_id = {t: i for i, t in enumerate(self.vocab)}
        self.idf = np.array([math.log((1 + self.n) / (1 + self.df[t])) + 1 for t in self.vocab])
        self.sparse = []
        for row in self.counts:
            ids = [self.term_id[t] for t in row if t in self.term_id]
            vals = normalize([(1 + math.log(row[self.vocab[i]])) * self.idf[i] for i in ids])
            self.sparse.append((np.array(ids, dtype=int), vals))
        rank = min(dimensions, len(self.vocab), self.n)
        if rank == 0:
            self.basis = np.zeros((len(self.vocab), 0))
            self.embeddings = np.zeros((self.n, 0))
            return
        rng = np.random.default_rng(seed)
        width = min(rank + 8, len(self.vocab), self.n)
        omega = rng.normal(size=(len(self.vocab), width))
        sketch = np.zeros((self.n, width))
        for i, (ids, vals) in enumerate(self.sparse):
            sketch[i] = vals @ omega[ids]
        # One power iteration improves the range estimate while keeping memory bounded.
        transpose = np.zeros((len(self.vocab), width))
        for i, (ids, vals) in enumerate(self.sparse):
            transpose[ids] += vals[:, None] * sketch[i]
        for i, (ids, vals) in enumerate(self.sparse):
            sketch[i] = vals @ transpose[ids]
        q, _ = np.linalg.qr(sketch, mode='reduced')
        small = np.zeros((q.shape[1], len(self.vocab)))
        for i, (ids, vals) in enumerate(self.sparse):
            small[:, ids] += q[i, :, None] * vals
        _, _, vt = np.linalg.svd(small, full_matrices=False)
        self.basis = vt[:rank].T
        self.embeddings = np.array([normalize(vals @ self.basis[ids]) for ids, vals in self.sparse])

    def bm25(self, query):
        scores = np.zeros(self.n)
        for t in set(tokenize(query)):
            if t not in self.df:
                continue
            idf = math.log(1 + (self.n - self.df[t] + .5) / (self.df[t] + .5))
            tf = np.array([c.get(t, 0) for c in self.counts], dtype=float)
            scores += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * self.lengths / self.avgdl))
        return scores

    def semantic(self, query):
        counts = Counter(tokenize(query))
        ids = [self.term_id[t] for t in counts if t in self.term_id]
        if not ids or self.basis.shape[1] == 0:
            return np.zeros(self.n)
        vals = normalize([(1 + math.log(counts[self.vocab[i]])) * self.idf[i] for i in ids])
        return self.embeddings @ normalize(vals @ self.basis[ids])

    def scores(self, query, weight=.15):
        lexical = self.bm25(query)
        latent = np.maximum(self.semantic(query), 0)
        if lexical.max() <= 0:
            return np.zeros(self.n)
        return (1 - weight) * lexical / lexical.max() + weight * latent

    def rank(self, query, weight=.15, limit=20):
        scores = self.scores(query, weight)
        return [(int(i), float(scores[i])) for i in np.argsort(-scores, kind='stable')[:limit] if scores[i] > 0]

def mmr(indices, scores, embeddings, limit=8, diversity=.25):
    """Diversify a candidate set without calling diversity a truth/quality score."""
    remaining = list(indices)
    selected = []
    while remaining and len(selected) < limit:
        def utility(i):
            redundancy = max((float(embeddings[i] @ embeddings[j]) for j in selected), default=0.)
            return (1 - diversity) * scores[i] - diversity * max(redundancy, 0)
        best = max(remaining, key=lambda i: (utility(i), -i))
        remaining.remove(best)
        selected.append(best)
    return selected
