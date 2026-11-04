# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paper Recommender is a macOS-only Python tool that uses Finder tags and semantic similarity to recommend research papers. Users tag favorite papers with red in Finder; the system finds similar papers using Sentence-BERT embeddings and tags recommendations with gray.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# === Local Recommendations ===
# Find similar papers in your local collection

python scripts/recommend.py local                    # Recommend 20% of candidates
python scripts/recommend.py local --subsample 1000   # Sample 1000 papers first
python scripts/recommend.py local --top-k 50         # Exactly 50 recommendations

# === arXiv Recommendations ===
# Discover new papers from arXiv preprints

python scripts/recommend.py arxiv                         # Default: ML + Physics, papers new since last run
python scripts/recommend.py arxiv --categories cond-mat   # Only condensed matter
python scripts/recommend.py arxiv --days 14 --include-seen -k 20  # re-rank 2 weeks incl. seen
python scripts/recommend.py arxiv --no-download           # Preview only
python scripts/recommend.py arxiv --full-text             # Use full text from HTML (slower)
```

## Architecture

```
src/paper_recommender/
├── tag_detector.py      # macOS Finder tag operations via xattr
├── pdf_extractor.py     # PDF text extraction (PyMuPDF primary, PyPDF2 fallback)
├── similarity_engine.py # Sentence-BERT embeddings + cosine similarity
└── arxiv_client.py      # arXiv API client for fetching and downloading papers

scripts/recommend.py     # Unified CLI with 'local' and 'arxiv' subcommands
```

**Core classes** (import from `paper_recommender`):
- `TagDetector` - Find/set Finder tags using extended attributes
- `PDFExtractor` - Extract text and metadata from PDFs
- `SimilarityEngine` - Generate embeddings, compute similarity, cache results
- `ArxivClient` - Search arXiv, fetch paper metadata, download PDFs

## Key Implementation Details

- **Caching**: Embeddings cached at `.cache/embeddings_cache.pkl` - delete to reset. Red-tagged arXiv refs are cached as `ref::<id>` (title+abstract)
- **Seen ledger**: `.cache/seen_arxiv.json` records every arXiv paper scored by a real (downloading) run; later runs skip those and anything already in the download dir. `--days` (default 3 business days) is only a minimum lookback, auto-extended to cover the gap since the last run. Don't go back to a rolling `--days 1` window: it missed every paper submitted 18:00-02:00 UTC (~30% of arXiv)
- **Scorer**: `--scorer logreg` (arXiv default) = logistic regression, refs vs. today's candidates + 3000 cached past candidates (excluding anything on disk, since past recommendations are on-topic and make bad negatives). `knn` and `centroid` are also available; local mode defaults to `centroid`
- **Daily entry point**: `run.sh` (`arxiv -k 20`); cron runs it on another machine
- **Model**: Uses `all-mpnet-base-v2` by default (768-dim, ~420MB); use `--model all-MiniLM-L6-v2` for faster/smaller alternative
- **PDF extraction**: First 10 pages only (`max_pages=10`) for efficiency
- **Tag colors**: red=6, orange=7, yellow=5, green=2, blue=4, purple=3, gray=1
- **Tags stored in**: `com.apple.metadata:_kMDItemUserTags` extended attribute (plist format)
- **Diversity**: `surprise_factor` samples from top-3x candidates to avoid echo chambers
- **Default directory**: iCloud Downloads (`~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/`)
- **arXiv API**: Uses Atom feed API with 3-second delay between requests (rate limiting)
- **arXiv categories**: Default includes `cond-mat`, `physics.comp-ph`, `physics.chem-ph`, `quant-ph`, `cs.LG`, `stat.ML` (queried in order; high-volume ML categories last so a mid-list rate-limit failure doesn't leave an ML-only pool)
- **arXiv similarity**: Default uses title+abstract; `--full-text` fetches full text from arXiv HTML pages (slower but more accurate, not all papers have HTML)
- **Author references**: By default uses both red-tagged papers and arXiv preprints from author `wang_l_1`; use `--refs author` for only arXiv preprints, `--refs tagged` for only red-tagged papers

## Platform Constraint

This project only works on macOS because it relies on Finder tags via extended attributes (`xattr` library).
