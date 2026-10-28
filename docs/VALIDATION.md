# Validation record

Validated October 27, 2026. Runtime: Python 3.12.14, NumPy 2.3.5, Node.js 24.22.1, and Chrome on Windows. Latency is specific to this machine and run.

## Automated checks

- **40 Python tests passed.** These cover retrieval, graph algorithms, ingestion, SQLite integrity, metric formulas, pairwise ML training and loss, country aggregation, theme/retraction handling, and GeoJSON integrity.
- **24 JavaScript tests passed.** These exercise the shipped search engine and eight hybrid plus eight learned-ranking Python/browser parity cases. Each parity case compares ten IDs and numeric scores.
- JavaScript syntax checks passed for `app/app.js` and `app/search.js`.
- The dataset rebuild reconciled 1,600 input rows to 1,598 unique works and passed SQLite foreign-key checks.
- External BEIR SciFact evaluation completed on the official train/test split. Results and uncertainty are in `outputs/benchmark.json` and `outputs/query_metrics.csv`.

```bash
python run.py
python scripts/verify.py
node tests/test_browser_engine.cjs
node --check app/app.js
node --check app/search.js
```

## Browser checks

Checked the actual app in Chrome:

- Search a natural-language earworm question and inspect source metadata.
- Switch Map/List; save a paper; compare two papers; close the dialog.
- Generate a five-paper trail and retain the saved collection after reload.
- Export a Markdown bibliography. The downloaded file contained five OpenAlex links and the expected heading.
- Combine open-access and publication-year filters.
- Submit an unknown query, verify the empty state and disabled trail button, and reset results.
- Inspect the benchmark and uncertainty disclosure in Behind the map.
- Switch to experimental ML ranking and inspect the model's underperformance disclosure.
- Filter Research atlas to music, select a country, export GeoJSON, and parse the resulting file: 177 boundary features, 35 with music papers, all carrying the correct theme label.
- Check a 390-by-844 viewport: list presentation defaults on mobile, Map remains available, and the document has no horizontal overflow. See `docs/desktop.png` and `docs/mobile.png`.

This is functional and responsive QA, not an accessibility certification or user study.

## Companion runtimes

**R 4.6.1 and MATLAB R2026b executed successfully.** Both independent PageRank replications assert maximum absolute disagreement from Python below 1e-9. R and MATLAB independently completed paired bootstrap analyses for both the hybrid and ML comparisons. These runtime checks are separate from the 64 Python/JavaScript tests. R/MATLAB random generators can yield different bootstrap interval endpoints from NumPy. Local software activation details and credentials are not part of the repository.

The fresh offline build also succeeded using only checked-in source files and the verified compressed source archive, with no raw API response cache and no network requests. See `outputs/offline_build_report.json`.

## Publication

The repository was pushed to [GitHub](https://github.com/DaniyalHayat/rabbithole), and its [initial GitHub Actions run](https://github.com/DaniyalHayat/rabbithole/actions/runs/40607105745) passed on Linux.

The final source was imported into [Figma Make](https://www.figma.com/make/AJhaZiufnubi0QBAiJPasT). I opened the Figma-hosted runtime directly and verified the working app, switched the ML mode, opened the atlas, and filtered it to music. `docs/figma-preview.png` captures that running preview. Figma's sharing dialog confirmed **Anyone can view**. The editor showed an intermittent M8 loading error in its AI chat area; the separate hosted preview worked.

The app is now published at [its existing Figma site](https://rabbit-hole-daniyalh-35298519.figma.site/). I updated that same destination after the initial publication. There is no claim of production adoption, improved learning, or a statistically significant retrieval improvement.

## Connected reading paths

I verified the updated Follow the thread interaction in the existing Make file and published app. It retains the original question, reveals attributed source-abstract excerpts, and offers related branches within that question's matching papers. Repeated clicks on the earworm example advance from involuntary musical imagery to related earworm research; Previous step and Back to the original retain the question. No URL changes are needed. JavaScript syntax and the 24 existing browser-engine checks passed. `docs/thread-following.png` captures the published interaction.
