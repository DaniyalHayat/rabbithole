# RabbitHole learned ranker

## Intended use

An inspectable experimental reranker for the first 50 hybrid-search candidates. It is available through the app's Ranking menu. **Hybrid search remains the default because the supervised model underperformed on held-out evaluation.** The learned score is a ranking utility, not a calibrated relevance or truth probability.

## Model and features

Pairwise logistic learning to rank, implemented with NumPy. For each labeled positive, I pair its features with up to 15 highly ranked nonpositive candidates and minimize `log(1 + exp(-w · (positive - negative)))` plus L2 regularization. Full-batch gradient descent uses 600 fixed steps at learning rate 0.08. Features are normalized BM25, positive LSA cosine, query-term coverage, title-term coverage, and log document length. Feature scales are fitted to training pair differences and exported with the five learned weights.

Unjudged candidates are treated as negatives for training. That is an approximation: absence of a relevance judgment is not verified nonrelevance. The model is linear, its candidate pool is truncated, and its training distribution is biomedical claims.

## Data and selection

BEIR SciFact: 5,183 corpus documents. The official training split contains 809 queries. A deterministic query-text hash partitions those into 645 fitting queries and 164 development queries. Identical query texts stay together, but semantically similar claims may cross that development split. I select L2 from 0.001, 0.01, and 0.1 on development nDCG@10, then refit on all 809 official training queries, producing 13,785 pairs. The 300 official test queries do not select the regularizer or fit weights. The test set had previously been used to evaluate the separate hybrid baseline; this is not a preregistered experiment.

## Held-out result

| Method | nDCG@10 | Recall@10 | MRR@10 |
|---|---:|---:|---:|
| Hybrid baseline | 0.67141 | 0.78744 | 0.63913 |
| Learned reranker | 0.64365 | 0.76550 | 0.61046 |

Paired nDCG difference: **-0.02777**, with a 95% paired bootstrap interval of **[-0.04468, -0.01146]**. The learned model's good development performance did not carry over to the official test split. I kept the better-performing hybrid method as the default rather than claiming an ML improvement. `outputs/ml_benchmark.json`, `outputs/ml_query_metrics.csv`, and `outputs/ml_model.json` contain the measured result and model artifact.

## Product boundary

The app uses a different, selected curiosity corpus. Its ranking features have the same definitions, and eight query cases verify Python/browser learned-ranking parity. That verifies implementation consistency, not cross-domain recommendation quality. Filtering can change the app's candidate pool before reranking. Reading trails still use the hybrid relevance/diversity heuristic after candidate selection. No user-behavior model, personal profiling, model service, or generative scientific answering is involved.

## Reproduce

```bash
python scripts/fetch_data.py --benchmark
python scripts/train_ranker.py
python run.py
python scripts/verify.py
node tests/test_browser_engine.cjs
```

Refreshing a public API is separate from reproducing the checked-in source snapshot. Model training uses the separately downloaded SciFact files and their recorded checksum.
