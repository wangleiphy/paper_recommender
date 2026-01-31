# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paper Recommender is a macOS-only Python tool that uses Finder tags and semantic similarity to recommend research papers. Users tag favorite papers with red in Finder; the system finds similar untagged papers using Sentence-BERT embeddings and tags recommendations with gray.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
# Or install as editable package
pip install -e .

# Run recommendations (default: 20% of candidates)
python scripts/recommend.py

# Fast mode: sample 1000 papers
python scripts/recommend.py --subsample 1000

# Custom directory with verbose output
python scripts/recommend.py --directory ~/Documents/Papers --subsample 500 --verbose

# Exact number of recommendations with 30% surprise factor
python scripts/recommend.py --top-k 50 --surprise 0.3

# Quick validation test
python examples/test_small_scale.py --sample-size 100
```

## Architecture

```
src/paper_recommender/
├── tag_detector.py      # macOS Finder tag operations via xattr
├── pdf_extractor.py     # PDF text extraction (PyMuPDF primary, PyPDF2 fallback)
└── similarity_engine.py # Sentence-BERT embeddings + cosine similarity

scripts/recommend.py     # Main CLI entry point orchestrating the workflow
```

**Core classes** (import from `paper_recommender`):
- `TagDetector` - Find/set Finder tags using extended attributes
- `PDFExtractor` - Extract text and metadata from PDFs
- `SimilarityEngine` - Generate embeddings, compute similarity, cache results

**Workflow**: Find red-tagged PDFs → Extract text → Generate embeddings → Compute average reference embedding → Rank candidates by cosine similarity → Tag top recommendations gray → Move duplicates

## Key Implementation Details

- **Caching**: Embeddings cached at `.cache/embeddings_cache.pkl` - delete to reset
- **Model**: Uses `all-MiniLM-L6-v2` (384-dim, ~90MB download on first run)
- **PDF extraction**: First 10 pages only (`max_pages=10`) for efficiency
- **Tag colors**: red=6, orange=7, yellow=5, green=2, blue=4, purple=3, gray=1
- **Tags stored in**: `com.apple.metadata:_kMDItemUserTags` extended attribute (plist format)
- **Diversity**: `surprise_factor` samples from top-3x candidates to avoid echo chambers
- **Default directory**: iCloud Downloads (`~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/`)
- **Duplicate handling**: Files with `(1)`, `(2)` patterns moved to OneDrive by default

## Platform Constraint

This project only works on macOS because it relies on Finder tags via extended attributes (`xattr` library).
