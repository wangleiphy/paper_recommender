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

python scripts/recommend.py arxiv                         # Default: ML + Physics, 7 days
python scripts/recommend.py arxiv --categories cond-mat   # Only condensed matter
python scripts/recommend.py arxiv --days 14 --top-k 20    # 2 weeks, 20 papers
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

- **Caching**: Embeddings cached at `.cache/embeddings_cache.pkl` - delete to reset
- **Model**: Uses `all-MiniLM-L6-v2` (384-dim, ~90MB download on first run)
- **PDF extraction**: First 10 pages only (`max_pages=10`) for efficiency
- **Tag colors**: red=6, orange=7, yellow=5, green=2, blue=4, purple=3, gray=1
- **Tags stored in**: `com.apple.metadata:_kMDItemUserTags` extended attribute (plist format)
- **Diversity**: `surprise_factor` samples from top-3x candidates to avoid echo chambers
- **Default directory**: iCloud Downloads (`~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/`)
- **arXiv API**: Uses Atom feed API with 3-second delay between requests (rate limiting)
- **arXiv categories**: Default includes `cs.LG`, `stat.ML`, `cond-mat`, `physics.comp-ph`, `physics.chem-ph`, `quant-ph`
- **arXiv similarity**: Default uses title+abstract; `--full-text` fetches full text from arXiv HTML pages (slower but more accurate, not all papers have HTML)
- **Author references**: By default uses both red-tagged papers and arXiv preprints from author `wang_l_1`; use `--refs author` for only arXiv preprints, `--refs tagged` for only red-tagged papers

## Platform Constraint

This project only works on macOS because it relies on Finder tags via extended attributes (`xattr` library).
