# Paper Recommender 📚

An intelligent paper recommendation system that uses macOS Finder tags and semantic similarity to help you discover research papers similar to your favorites.

## 🎯 Features

- **Tag-Based Discovery**: Tag your favorite papers with red in Finder, get recommendations based on ALL of them
- **Semantic Understanding**: Uses Sentence-BERT to understand paper content, not just keywords
- **Smart Recommendations**: Automatically recommends ~20% of your papers (adjustable)
- **Surprise Factor**: Adds variety to avoid echo chambers - includes some "hidden gems"
- **Auto-Tagging**: Marks recommendations with "Gray" tag in Finder
- **Fast & Free**: Runs locally with caching - no API costs, fast subsequent runs
- **Large Scale**: Tested on 17,000+ papers

## 📦 Installation

### Prerequisites
- macOS (uses Finder tags)
- Python 3.8+

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/paper-recommender.git
cd paper-recommender

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## 🚀 Usage

### Basic Usage

```bash
# Recommend 20% of ALL papers (processes everything)
python scripts/recommend.py

# Fast mode: sample 1000 papers, recommend 20%
python scripts/recommend.py --subsample 1000

# Sample 500 papers, recommend 30%
python scripts/recommend.py --subsample 500 --percent 30

# Exact number of recommendations
python scripts/recommend.py --top-k 50

# Adjust surprise/diversity
python scripts/recommend.py --subsample 1000 --surprise 0.3  # 30% surprises

# Verbose output
python scripts/recommend.py --subsample 1000 --verbose
```

### Examples

```bash
# Quick test: sample 100 papers
python scripts/recommend.py --subsample 100 --verbose

# Conservative: sample 500, recommend 10%, minimal surprises
python scripts/recommend.py --subsample 500 --percent 10 --surprise 0.1

# Exploratory: sample 2000, recommend 30%, lots of variety
python scripts/recommend.py --subsample 2000 --percent 30 --surprise 0.4

# Full collection (slow first time, fast with cache)
python scripts/recommend.py --percent 20

# Custom directory
python scripts/recommend.py --directory ~/Documents/Papers --subsample 1000

# Don't auto-tag recommendations
python scripts/recommend.py --subsample 1000 --no-tag
```

### Try the Examples

```bash
# Quick demo with small sample
python examples/demo_diversity.py

# Test Gray tagging
python examples/test_tagging.py

# Small scale test (100 papers)
python examples/test_small_scale.py --sample-size 100

# Verify all red-tagged papers are used
python examples/verify_all_refs_used.py

# Estimate time and cost for full run
python examples/estimate_cost.py
```

## 📖 How It Works

1. **Tag Detection**: Scans for red-tagged PDF files using macOS extended attributes
2. **Text Extraction**: Extracts text from ALL red-tagged papers (no sampling!)
3. **Embedding Generation**: Creates semantic embeddings using Sentence-BERT
4. **Similarity Computation**: Computes average embedding from all your favorites
5. **Smart Ranking**: Ranks papers by similarity with diversity factor
6. **Auto-Tagging**: Tags top recommendations with "Gray" tag

### Key Algorithms

- **Reference Pool**: Uses ALL red-tagged papers to capture complete preferences
- **Similarity Metric**: Cosine similarity between embeddings
- **Diversity Injection**: Samples from top 3x range for variety
- **Percentage-Based**: Recommends configurable % of candidates (default 20%)

## 📁 Project Structure

```
paper_recommender/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
├── LICENSE                      # MIT license
├── .gitignore                   # Git ignore rules
│
├── src/
│   └── paper_recommender/       # Core package
│       ├── __init__.py          # Package initialization
│       ├── tag_detector.py      # macOS Finder tag detection
│       ├── pdf_extractor.py     # PDF text extraction
│       └── similarity_engine.py # Semantic similarity computation
│
├── scripts/
│   └── recommend.py             # Main recommendation script
│
├── examples/
│   ├── demo_diversity.py        # Demo: diversity features
│   ├── demo_with_tagging.py     # Demo: with Gray tagging
│   ├── test_small_scale.py      # Test on small sample
│   ├── test_tagging.py          # Test Gray tagging
│   ├── verify_all_refs_used.py  # Verify all refs used
│   └── estimate_cost.py         # Cost/time estimation
│
├── docs/
│   ├── FEATURES.md              # Detailed feature documentation
│   └── USAGE_NOTES.md           # Usage notes and tips
│
└── venv/                        # Virtual environment (not in git)
```

## ⚙️ Configuration

### Recommendation Percentage

By default, recommends **20% of candidate papers**. Adjust with `--percent`:

```bash
python scripts/recommend.py --percent 15  # Recommend 15%
python scripts/recommend.py --percent 30  # Recommend 30%
```

### Surprise Factor

Controls diversity (0.0 = pure similarity, 1.0 = maximum variety):

```bash
python scripts/recommend.py --surprise 0.0  # No surprises
python scripts/recommend.py --surprise 0.2  # 20% surprises (default)
python scripts/recommend.py --surprise 0.5  # 50% surprises
```

**Surprise papers** are sampled from ranks just below the top (e.g., ranks 11-30 instead of 1-10).

## 📊 Performance

### Time Estimates (17,435 papers)

- **First run**: ~3 hours (extracts + embeds all papers)
- **Model download**: ~3 minutes (one-time, 90MB)
- **Subsequent runs**: ~10 seconds (uses cache!)
- **New papers**: ~0.5 seconds per paper

### Cost

- **Software**: $0.00 (runs locally, no APIs)
- **Electricity**: ~$0.01 per full run
- **vs OpenAI Embeddings**: Saves ~$1.74 per run

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Support for other operating systems (Linux, Windows)
- Additional similarity metrics
- Topic clustering for multi-topic recommendations
- Web interface
- Citation network analysis

## 📝 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

Built with:
- [Sentence-Transformers](https://www.sbert.net/) for embeddings
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF extraction
- [scikit-learn](https://scikit-learn.org/) for similarity computation

## 📚 Documentation

- [FEATURES.md](docs/FEATURES.md) - Detailed feature documentation
- [USAGE_NOTES.md](docs/USAGE_NOTES.md) - Usage notes and tips

## 🐛 Troubleshooting

### "No red-tagged PDFs found"
Tag some papers with red in Finder first (Right-click → Tags → Red)

### "Could not extract text"
Some PDFs are scanned images. Consider using OCR preprocessing.

### "Module not found"
Make sure you're in the virtual environment: `source venv/bin/activate`

### Slow first run
This is normal - extracting and embedding 17K papers takes time. Subsequent runs are fast!

## 📧 Contact

Questions? Issues? Open an issue on GitHub!
