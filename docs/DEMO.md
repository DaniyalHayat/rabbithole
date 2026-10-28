# My five-minute demo

1. Open the app and search **Why do songs get stuck in my head?** The matching research is about involuntary musical imagery. Explain the explicit synonym expansion and how it differs from a generated answer.
2. Select a graph node, then switch to List. Follow an original DOI link. Explain that citation, shared-topic, and text-similarity connections have different meanings.
3. Check Open access and select Since 2020. The results and selected paper change together.
4. Press Compare on one paper, choose a second paper, and press Compare again. The comparison shows source metadata and abstracts without inventing agreement or contradiction.
5. Build a reading trail, then open My trails. Export the bibliography. Reload and verify that the saved collection persists locally.
6. Switch Ranking to the experimental ML model, then open Behind the map. Explain why the stronger hybrid baseline remains the default.
7. Open Research atlas, filter to one thread, select a country, and export GeoJSON. Explain why affiliation counts are not national research rankings.
8. Open Behind the map. Show the measured benchmark, its uncertainty interval, and what the benchmark does not validate.

## Questions I should be ready to answer

- **Why not an LLM wrapper?** I wanted to own retrieval, graph integrity, explainability, evaluation, and an offline product. The statistical engine is inspectable and needs no model service.
- **Why LSA?** It is a lightweight semantic baseline with deterministic training and browser-portable projections. It is weaker than modern pretrained embeddings on many tasks. A useful next experiment is a measured comparison against those embeddings, rather than assuming they are better for this corpus.
- **Why not call the map a consensus graph?** References and similar wording do not establish agreement or evidence strength. Reading the full papers and applying subject expertise is still necessary.
- **Did the hybrid search win?** It scored slightly higher on the held-out benchmark, but the confidence interval includes zero. I report the actual scores and avoid an unsupported significance claim.
- **What would I change at larger scale?** A sparse inverted index and ANN service, background ingestion jobs, incremental graph updates, source-level monitoring, an independently judged curiosity benchmark, and user testing. The current app deliberately ships a modest fixed snapshot.
- **What did I validate?** Python/SQL logic, JavaScript engine parity, ML inference parity, data integrity, external retrieval benchmarks, GIS export, and desktop/mobile interactions. I also executed R and MATLAB replications against Python reference outputs.
