"""Graph algorithms; only verified in-corpus references become citation edges."""
from __future__ import annotations
from collections import defaultdict, deque
import numpy as np

def pagerank(n, edges, damping=.85, tolerance=1e-11, iterations=300, personalization=None):
    if n < 1:
        return np.array([])
    prior = np.ones(n) / n if personalization is None else np.asarray(personalization, dtype=float)
    if len(prior) != n or np.any(prior < 0) or prior.sum() <= 0:
        raise ValueError('Invalid personalization')
    prior = prior / prior.sum()
    adjacency = defaultdict(set)
    for a, b in edges:
        if not (0 <= a < n and 0 <= b < n):
            raise ValueError('Dangling edge')
        if a != b:
            adjacency[a].add(b)
    rank = prior.copy()
    for _ in range(iterations):
        nxt = (1 - damping) * prior + damping * sum(rank[i] for i in range(n) if not adjacency[i]) * prior
        for i, targets in adjacency.items():
            if targets:
                for j in targets:
                    nxt[j] += damping * rank[i] / len(targets)
        if np.abs(nxt - rank).sum() < tolerance:
            return nxt / nxt.sum()
        rank = nxt
    return rank / rank.sum()

def shortest_path(start, end, edges):
    adjacency = defaultdict(set)
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    queue = deque([[start]])
    seen = {start}
    while queue:
        path = queue.popleft()
        if path[-1] == end:
            return path
        for other in sorted(adjacency[path[-1]]):
            if other not in seen:
                seen.add(other)
                queue.append(path + [other])
    return []

def components(n, edges):
    parent = list(range(n))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in edges:
        parent[root(a)] = root(b)
    groups = defaultdict(list)
    for i in range(n):
        groups[root(i)].append(i)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]))
