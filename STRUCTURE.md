# Repository Structure

Clean, professional organization of the Paper Recommender project.

## Directory Tree

```
paper_recommender/
│
├── 📄 README.md                 # Main documentation
├── 📄 QUICKSTART.md             # 5-minute getting started guide
├── 📄 CONTRIBUTING.md           # Contribution guidelines
├── 📄 LICENSE                   # MIT license
├── 📄 STRUCTURE.md              # This file
│
├── ⚙️  setup.py                  # Python package setup
├── 📋 requirements.txt          # Python dependencies
├── 🚫 .gitignore                # Git ignore rules
│
├── 📦 src/                      # Source code
│   └── paper_recommender/
│       ├── __init__.py          # Package initialization
│       ├── tag_detector.py      # macOS tag detection (223 lines)
│       ├── pdf_extractor.py     # PDF text extraction (212 lines)
│       └── similarity_engine.py # Similarity computation (273 lines)
│
├── 🎯 scripts/                  # Main executable scripts
│   └── recommend.py             # Main recommendation script (292 lines)
│
├── 🎨 examples/                 # Examples and demos
│   ├── README.md                # Examples documentation
│   ├── demo_diversity.py        # Diversity feature demo
│   ├── demo_with_tagging.py     # Full workflow demo
│   ├── test_small_scale.py      # Small-scale testing
│   ├── test_tagging.py          # Tag functionality test
│   ├── verify_all_refs_used.py  # Verify reference usage
│   └── estimate_cost.py         # Cost/time estimation
│
├── 📚 docs/                     # Documentation
│   ├── README.md                # Documentation index
│   ├── FEATURES.md              # Detailed features
│   └── USAGE_NOTES.md           # Usage notes and tips
│
├── 🔧 venv/                     # Virtual environment (not in git)
│   ├── bin/
│   ├── lib/
│   └── ...
│
└── 💾 .cache/                   # Embedding cache (not in git)
    └── embeddings_cache.pkl
```

## File Categories

### 📄 Documentation (Root)
- **README.md**: Complete project documentation
- **QUICKSTART.md**: Get started in 5 minutes
- **CONTRIBUTING.md**: How to contribute
- **STRUCTURE.md**: Repository organization (this file)
- **LICENSE**: MIT license

### 📦 Source Code (`src/paper_recommender/`)
Core Python package with three main modules:
- **tag_detector.py**: macOS Finder tag detection and manipulation
- **pdf_extractor.py**: PDF text extraction and metadata
- **similarity_engine.py**: Semantic similarity and recommendations

### 🎯 Scripts (`scripts/`)
Production-ready executable scripts:
- **recommend.py**: Main recommendation engine

### 🎨 Examples (`examples/`)
Example scripts, demos, and tests:
- Demos showing features
- Small-scale tests
- Verification scripts
- Cost estimation

### 📚 Documentation (`docs/`)
Extended documentation:
- Feature details
- Usage notes
- Technical documentation

## Import Structure

### From Examples or Scripts
```python
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector, PDFExtractor, SimilarityEngine
```

### As Installed Package
```python
from paper_recommender import TagDetector, PDFExtractor, SimilarityEngine
```

## Key Features of Organization

### ✅ Separation of Concerns
- Source code in `src/`
- Scripts in `scripts/`
- Examples in `examples/`
- Documentation in `docs/`

### ✅ Clear Entry Points
- Main script: `scripts/recommend.py`
- Quick demos: `examples/`
- Full docs: `README.md` + `docs/`

### ✅ Professional Structure
- Standard Python package layout
- Easy to install (`pip install -e .`)
- Clear licensing and contribution guidelines

### ✅ User-Friendly
- Quick start guide for beginners
- Examples for different use cases
- Comprehensive documentation

## Lines of Code

| Component | Lines | Purpose |
|-----------|-------|---------|
| tag_detector.py | 223 | Tag detection and manipulation |
| pdf_extractor.py | 212 | PDF text extraction |
| similarity_engine.py | 273 | Similarity computation |
| recommend.py | 292 | Main recommendation script |
| **Total Core** | **1,000** | **Core functionality** |

## Dependencies

Managed in `requirements.txt`:
- PyMuPDF: PDF processing
- Sentence-Transformers: Semantic embeddings
- scikit-learn: Similarity computation
- xattr: macOS tag access
- Other: numpy, pandas, tqdm

## Ignored Files

Via `.gitignore`:
- `venv/` - Virtual environment
- `__pycache__/` - Python cache
- `.cache/` - Embedding cache
- `*.pyc` - Compiled Python
- `.DS_Store` - macOS metadata

## Future Enhancements

Potential additions:
- `tests/` directory for unit tests
- `notebooks/` for Jupyter analysis
- `data/` for sample data
- `config/` for configuration files
- `.github/` for CI/CD workflows

