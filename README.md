# Paper Recommender

Find papers similar to your favorites using semantic similarity.

1. Tag papers you like with **red** in Finder
2. Run the recommender
3. Similar papers get tagged **gray**

## Installation

```bash
git clone <repo>
cd paper_recommender
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

```bash
# First: tag some papers with RED in Finder (right-click → Tags → Red)

# Find similar papers in your local collection
python scripts/recommend.py local

# Discover similar papers from arXiv
python scripts/recommend.py arxiv
```

## Usage

### Common Flags (both modes)

| Flag | Description |
|------|-------------|
| `-k, --top-k N` | Recommend N papers (default: 10) |
| `-n, --max-candidates N` | Consider at most N candidates (for speed) |
| `-d, --directory DIR` | Paper directory (default: iCloud Downloads) |
| `-s, --surprise F` | Diversity 0-1, higher=more variety (default: 0.2) |
| `-v, --verbose` | Show detailed progress |
| `--no-tag` | Don't tag recommendations |
| `--no-recursive` | Don't search subdirectories |

### Local Mode

Find similar papers in your existing PDF collection.

```bash
python scripts/recommend.py local              # Recommend 10 papers
python scripts/recommend.py local -k 50        # Recommend 50 papers
python scripts/recommend.py local -n 1000      # Sample 1000 candidates (faster)
python scripts/recommend.py local -k 20 -n 500 # Top 20 from 500 candidates
```

### arXiv Mode

Discover new papers from recent arXiv preprints.

```bash
python scripts/recommend.py arxiv                   # 10 papers from last 7 days
python scripts/recommend.py arxiv -k 20             # 20 papers
python scripts/recommend.py arxiv --days 14         # Last 2 weeks
python scripts/recommend.py arxiv -c cond-mat       # Only condensed matter
python scripts/recommend.py arxiv --no-download     # Preview without downloading
```

**arXiv-specific flags:**

| Flag | Description |
|------|-------------|
| `-c, --categories` | arXiv categories to search |
| `--days N` | Look back N days (default: 7) |
| `--no-download` | Preview only (don't download) |

**Default categories:** `cs.LG`, `stat.ML`, `cond-mat`, `physics.comp-ph`, `physics.chem-ph`, `quant-ph`

**More categories:**
| Category | Description |
|----------|-------------|
| `cond-mat` | All Condensed Matter |
| `cond-mat.supr-con` | Superconductivity |
| `cond-mat.str-el` | Strongly Correlated Electrons |
| `cond-mat.mtrl-sci` | Materials Science |
| `quant-ph` | Quantum Physics |
| `physics.comp-ph` | Computational Physics |
| `hep-lat` | Lattice QCD |
| `cs.LG` | Machine Learning |
| `stat.ML` | Machine Learning (Statistics) |

## Examples

```bash
# Fast local search: sample 1000 papers, recommend top 20
python scripts/recommend.py local -k 20 -n 1000

# arXiv condensed matter papers from last 2 weeks
python scripts/recommend.py arxiv -c cond-mat --days 14 -k 15

# arXiv ML + quantum physics, preview only
python scripts/recommend.py arxiv -c cs.LG quant-ph --no-download

# Verbose mode to see progress
python scripts/recommend.py local -v
```

## How It Works

1. Finds your red-tagged PDFs (favorites)
2. Extracts text and creates semantic embeddings
3. Ranks candidates by similarity to your favorites
4. Tags top matches with gray

Embeddings are cached (`.cache/`) for fast subsequent runs.

## Requirements

- macOS (uses Finder tags)
- Python 3.8+
