"""Small, inspectable pairwise learning-to-rank model trained with NumPy."""
from __future__ import annotations
import math
import numpy as np
from .search import tokenize

FEATURES = ['normalized_bm25', 'positive_lsa_cosine', 'query_coverage', 'title_coverage', 'log_document_length']

def features(index, query):
    lexical = index.bm25(query)
    latent = np.maximum(index.semantic(query), 0)
    terms = set(tokenize(query))
    denom = max(len(terms), 1)
    coverage = [len(terms & set(c)) / denom for c in index.counts]
    title = [len(terms & set(tokenize(d['title']))) / denom for d in index.docs]
    return np.column_stack([lexical / max(float(lexical.max()), 1e-12), latent, coverage, title, np.log1p(index.lengths) / 10])

def fit_pairwise(differences, l2=.01, steps=600):
    """Minimize log(1+exp(-w.(positive-negative))) + L2 with fixed full-batch steps."""
    differences = np.asarray(differences, dtype=float)
    if differences.ndim != 2 or not len(differences) or not np.isfinite(differences).all():
        raise ValueError('Finite, nonempty pair differences are required')
    scale = np.maximum(differences.std(axis=0), .01)
    x = differences / scale
    weights = np.zeros(x.shape[1])
    losses = []
    for _ in range(steps):
        margins = np.clip(x @ weights, -40, 40)
        error = 1 / (1 + np.exp(margins))
        gradient = -(x.T @ error) / len(x) + l2 * weights
        weights -= .08 * gradient
        losses.append(float(np.logaddexp(0, -margins).mean() + .5 * l2 * (weights @ weights)))
    return {'weights': weights.tolist(), 'scale': scale.tolist(), 'l2': l2, 'steps': steps, 'feature_names': FEATURES, 'loss_first': losses[0], 'loss_last': losses[-1]}

def predict(model, x):
    return (np.asarray(x) / np.asarray(model['scale'])) @ np.asarray(model['weights'])
