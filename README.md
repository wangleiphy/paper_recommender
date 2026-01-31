# Paper Recommender

Recommend research papers based on macOS Finder tags and semantic similarity.

Tag your favorite papers with **red** in Finder. The system finds similar untagged papers and marks them with **gray**.

## Requirements

- macOS (uses Finder tags)
- Python 3.8+

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Tag some papers with red in Finder first, then:

# Quick test (sample 1000 papers)
python scripts/recommend.py --subsample 1000

# Full run (slow first time, cached after)
python scripts/recommend.py

# More options
python scripts/recommend.py --help
```

### Options

| Flag | Description |
|------|-------------|
| `--subsample N` | Sample N papers for faster processing |
| `--percent P` | Recommend P% of candidates (default: 20) |
| `--surprise S` | Diversity factor 0-1 (default: 0.2) |
| `--top-k K` | Exact number of recommendations |
| `--no-tag` | Don't auto-tag recommendations |
| `--verbose` | Show detailed progress |

## How It Works

1. Finds all red-tagged PDFs (your favorites)
2. Extracts text and computes embeddings (cached)
3. Ranks other papers by similarity to your favorites
4. Tags top recommendations with gray

Uses [Sentence-BERT](https://www.sbert.net/) for semantic similarity. Runs locally, no API costs.

## Troubleshooting

**No red-tagged PDFs found**: Tag papers with red in Finder (Right-click → Tags → Red)

**Module not found**: Activate venv: `source venv/bin/activate`

**Slow first run**: Normal - embeddings are cached for fast subsequent runs
