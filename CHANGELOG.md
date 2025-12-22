# Changelog

## [1.1.0] - 2025-12-22

### Major Refactoring

#### Changed
- **Unified command interface**: Merged `recommend_subset.py` functionality into `recommend.py`
- Added `--subsample N` flag to randomly sample N candidate papers
- Simplified user experience: one command instead of multiple scripts

#### Removed
- `scripts/recommend_subset.py` - functionality merged into `recommend.py`

#### Migration
```bash
# Old
python scripts/recommend_subset.py --sample 1000

# New
python scripts/recommend.py --subsample 1000
```

## [1.0.0] - 2025-12-22

### Repository Reorganization
Complete restructuring of the repository for better organization and maintainability.

#### Changed
- **Moved core modules** to `src/paper_recommender/` package
  - `tag_detector.py`
  - `pdf_extractor.py`
  - `similarity_engine.py`
  
- **Moved main script** to `scripts/` directory
  - `recommend.py`

- **Moved examples and tests** to `examples/` directory
  - `demo_diversity.py`
  - `demo_with_tagging.py`
  - `test_small_scale.py`
  - `test_tagging.py`
  - `verify_all_refs_used.py`
  - `estimate_cost.py`

- **Moved documentation** to `docs/` directory
  - `FEATURES.md`
  - `USAGE_NOTES.md`

#### Added
- **Package initialization**: `src/paper_recommender/__init__.py`
- **Setup script**: `setup.py` for proper package installation
- **License**: MIT license file
- **Quick start guide**: `QUICKSTART.md` for new users
- **Contributing guide**: `CONTRIBUTING.md` for contributors
- **Structure documentation**: `STRUCTURE.md` showing repository layout
- **Changelog**: This file
- **Directory READMEs**: Documentation for `examples/` and `docs/`

#### Updated
- **Main README**: Complete rewrite with new structure
- **Import statements**: All scripts updated to use new package structure
- **.gitignore**: Enhanced with additional patterns

### Features

#### Smart Recommendations
- **Percentage-based**: Automatically recommend ~20% of papers (configurable)
- **Surprise factor**: Add diversity with configurable surprise percentage (default 20%)
- **No reference sampling**: Always uses ALL red-tagged papers

#### Auto-tagging
- Automatically tag recommendations with green "Recommended" tag in Finder
- Optional: disable with `--no-tag` flag

#### Performance
- Embedding caching for fast subsequent runs
- Parallel processing where possible
- Optimized for large collections (tested on 17K+ papers)

### Technical Details

#### Lines of Code
- Core modules: ~700 lines
- Main script: ~290 lines
- Examples: ~600 lines
- Total: ~1,600 lines of Python

#### Dependencies
- PyMuPDF >= 1.23.0
- Sentence-Transformers >= 2.2.0
- scikit-learn >= 1.3.0
- xattr >= 1.0.0
- And more (see requirements.txt)

### Breaking Changes
None (first stable release)

### Migration Guide
If you were using an older version:

```bash
# Old usage (if files were in root)
python recommend.py

# New usage
python scripts/recommend.py

# Or install as package
pip install -e .
python -m paper_recommender.recommend
```

### Notes
- All imports updated to use new package structure
- Backward compatibility maintained for command-line interface
- No changes to algorithm or output format

