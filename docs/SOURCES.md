# Sources and attribution

## OpenAlex

- Provider: [OpenAlex](https://openalex.org), a project of OurResearch.
- API and authentication: [OpenAlex API](https://help.openalex.org/api/) and [authentication](https://help.openalex.org/api/authentication/).
- Work fields and abstract representation: [Work attributes](https://help.openalex.org/data/works/attributes/).
- Data license: [OpenAlex data licensing](https://help.openalex.org/data/licensing/). OpenAlex releases its dataset under CC0. Underlying publisher text and linked full papers may have separate rights; the source snapshot contains metadata and the abstract indexes supplied by the API, not downloaded full papers. The repository's MIT software license does not override third-party rights.
- The exact anonymous query URLs, themes, row counts, and response checksums are recorded in `data/raw/manifest.json`.
- Source snapshot assembled October 27, 2026. A fixed publication cutoff does not make citation counts or metadata historically vintage-correct.
- No API keys, user emails, authentication cookies, or personal browsing data are read by the downloader.

## SciFact / BEIR

- [BEIR repository and dataset instructions](https://github.com/beir-cellar/beir).
- Dataset download: `https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip`.
- [AllenAI SciFact](https://github.com/allenai/scifact), Wadden et al., *Fact or Fiction: Verifying Scientific Claims*, EMNLP 2020.
- [SciFact license details](https://github.com/allenai/scifact/blob/master/LICENSE.md): abstracts originate from S2ORC under ODC-By 1.0; claims and other dataset components follow their upstream terms. See that license before redistribution or commercial use. This project uses the benchmark for an independent, noncommercial portfolio evaluation.
- Benchmark raw documents and judgments are downloaded on demand and are excluded from Git. The repository contains the download checksum, aggregate metrics, and derived per-query metric pairs. The bundled curiosity app is based on OpenAlex, not on SciFact's biomedical corpus.

## Geography

Made with Natural Earth 1:110m country boundaries, [public domain](https://www.naturalearthdata.com/about/terms-of-use/). The exact [source file](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson) and SHA-256 manifest are checked in. Institution-country codes come from the same OpenAlex authorship metadata already included in the locked research source snapshot. No personal locations are inferred.

## Method references

- Robertson and Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009), [DOI](https://doi.org/10.1561/1500000019).
- Deerwester et al., *Indexing by Latent Semantic Analysis* (1990), [DOI](https://doi.org/10.1002/(SICI)1097-4571(199009)41:6%3C391::AID-ASI1%3E3.0.CO;2-9).
- Carbonell and Goldstein, *The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries* (1998), [DOI](https://doi.org/10.1145/290941.291025).

The implementation is my own compact educational implementation of these established methods. I do not claim to have invented BM25, LSA, PageRank, or MMR.
