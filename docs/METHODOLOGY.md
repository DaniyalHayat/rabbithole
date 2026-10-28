# How I built RabbitHole

I wanted a research app that makes it easy to follow a question without pretending that a search result is a scientific answer. I separated three things throughout the product: source text, citation relationships, and statistical similarity.

## Data pipeline

I retrieved the first 100 relevance-ranked English-language results for each of 16 fixed searches through OpenAlex, with a publication cutoff of October 27, 2026. The searches cover eight curiosity themes. This is a convenience sample, not a representative census of research.

The pipeline accepts a work only if its OpenAlex ID, title, and publication year pass validation. It merges repeated IDs, reconstructs supplied inverted-index abstracts in position order, and preserves the source query and file for each accepted occurrence. Source response checksums are in `data/raw/manifest.json`. The deterministic compressed source snapshot has its own SHA-256 in `data/snapshot_checksum.txt`.

The locked snapshot contains 1,600 source rows, 1,598 distinct works, 518 topic IDs, and 2,437 directed references with both endpoints present. Two repeated work IDs were merged. No rows required quarantine under the implemented rules. Different IDs can still refer to bibliographically similar works; I do not claim perfect entity resolution. 1,297 works have source abstracts and 1,072 have an open-access flag. Two retracted records remain in the auditable source but are excluded from browser discovery, related suggestions, and trails.

I store normalized papers, topics, many-to-many topic memberships, citations, and provenance in SQLite, with primary keys, foreign keys, value constraints, and an FTS5 index. A rebuild writes a temporary database, validates foreign keys, closes the connection, and replaces the previous database. It does not mutate synced project references.

## Retrieval

1. I lowercase and tokenize alphanumeric words, discard one-character words, and remove a fixed English stop list.
2. BM25 uses `k1=1.2` and `b=0.75`. The searchable document repeats its title twice, then includes the supplied abstract and topic labels. This is a deliberate field-weighting heuristic.
3. I form log-TF / smoothed-IDF vectors, excluding vocabulary terms occurring in fewer than two documents from the latent model. Those terms remain available to BM25.
4. A seeded randomized range approximation, one power iteration, QR decomposition, and small-matrix SVD produce 48-dimensional latent vectors. Document and query projections are normalized. Missing or out-of-vocabulary latent vectors safely become zero vectors.
5. Search fuses normalized BM25 with positive latent cosine similarity: `0.85 * normalized_BM25 + 0.15 * positive_cosine`. An entirely unknown query returns no matches rather than unrelated recommendations.

This is **latent semantic analysis**, not a pretrained neural embedding model or LLM. It is small enough to ship to a browser. The JavaScript implementation uses rounded exported vectors and basis weights. Eight cross-language query cases check the first ten ranked IDs and numerical score agreement within 0.0003. Browser question expansion adds explicit, documented terms for six phrase patterns, such as mapping "songs stuck in my head" to "involuntary musical imagery". Unexpanded queries are used in the parity tests and external benchmark.

## Graph and reading trails

The source citation graph preserves direction from citing paper to referenced paper. The visual map shows up to 24 search results; it is a small view of a larger graph, not the entire corpus. Solid arrows are actual references. Dashed lines are shared OpenAlex topics. Dotted lines are latent-text connections. Hover titles explain the connection type. One displayed edge per pair avoids overlapping duplicate lines.

I compute PageRank with damping 0.85 and redistribute dangling-node mass. The graph module also provides personalized PageRank, weak components, and shortest undirected citation paths. PageRank is an analytical output and replication exercise; I do not secretly blend it into search relevance or treat it as a measure of scientific validity.

Suggested trails select five papers using a relevance/diversity tradeoff: `0.75 * relevance - 0.25 * maximum similarity to an already selected paper`. The first step receives a small 0.12 bonus for source records marked as reviews. This is a heuristic reading order, not an inferred prerequisite curriculum. Saved papers remain in browser local storage and can be exported as a Markdown bibliography.

## External evaluation

I used BEIR's SciFact retrieval dataset, which contains 5,183 abstracts. I selected the fusion weight from `{0, 0.1, 0.15, 0.25, 0.4}` using the official 809 training queries and their relevance judgments. The corpus supports unsupervised indexing; no test judgments influence the latent representation or weight selection. I then evaluated the selected 0.15 weight on the 300 official test queries.

| Method | nDCG@10 | Recall@10 | MRR@10 |
|---|---:|---:|---:|
| BM25 | 0.66595 | 0.78244 | 0.63373 |
| Train-selected BM25 + LSA | 0.67141 | 0.78744 | 0.63913 |

The paired nDCG@10 difference is **0.00546**, with a percentile bootstrap 95% interval of **[-0.00129, 0.01241]** from 5,000 query-pair resamples and seed 42. The interval includes zero, so I do not claim a statistically established improvement. Raw query-pair results are in `outputs/query_metrics.csv`. Latency in the recorded Python run was 16.25 ms median and 29.92 ms at the 95th percentile; it is hardware-specific and excludes indexing, network, and browser rendering.

SciFact measures biomedical abstract retrieval, not curiosity search, factual correctness, scientific consensus, or user learning. It does not evaluate the graph display, heuristic synonym expansion, or reading-trail quality. My next evaluation would use independently judged curiosity questions and a usability study. There is no such study in this project yet.

## Added machine learning and geography

I also trained a supervised pairwise logistic ranking model on 13,785 SciFact comparisons, with regularization selected within the official train split. Its held-out nDCG@10 was 0.64365, below the hybrid baseline's 0.67141. I kept it as an experimental app mode and retained the stronger hybrid default. The [model card](MODEL_CARD.md) documents the training assumptions, weights, uncertainty, and failed generalization.

The research atlas aggregates distinct non-retracted papers by listed institution country, covering 77 countries and 1,207 papers with country metadata. I deduplicate paper-country pairs and preserve international collaborations as multiple country memberships. Natural Earth boundaries supply the WGS84 polygons. [GIS.md](GIS.md) explains sampling bias, non-additive counts, GeoJSON export, and Esri licensing.

I executed independent R and MATLAB graph/statistical replications; their PageRank calculations matched the Python reference within the scripts' 1e-9 tolerance. Python/browser parity covers both hybrid retrieval and learned ranking.

## Product boundaries

The app displays supplied abstract text and metadata. It does not generate scientific conclusions, assess agreement or contradiction, diagnose anyone, or claim that a citation establishes evidence quality. Publication types, citation counts, open-access flags, abstracts, and retraction flags come from OpenAlex and can be missing, stale, or noisy. Some source abstracts include boilerplate or other text. Following a source link may lead to a paywall. English-only sampling and query selection create coverage biases.
