# Contributing to Paper Recommender

Thank you for considering contributing to Paper Recommender! This document provides guidelines and information for contributors.

## Ways to Contribute

### 🐛 Report Bugs
- Use GitHub Issues
- Include: OS version, Python version, error messages
- Provide minimal reproducible example if possible

### 💡 Suggest Features
- Open an issue with `[Feature Request]` in title
- Explain use case and expected behavior
- Discuss before implementing major features

### 📝 Improve Documentation
- Fix typos, clarify confusing sections
- Add examples or use cases
- Improve code comments

### 🔧 Submit Code
- Bug fixes
- New features (discuss first)
- Performance improvements
- Tests

## Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/paper-recommender.git
cd paper-recommender

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Code Style

- Follow PEP 8
- Use type hints where appropriate
- Add docstrings for public functions/classes
- Keep functions focused and small

## Project Structure

```
paper_recommender/
├── src/paper_recommender/    # Core package
│   ├── tag_detector.py        # Tag detection
│   ├── pdf_extractor.py       # PDF text extraction
│   └── similarity_engine.py   # Similarity computation
├── scripts/                   # Main scripts
├── examples/                  # Example/demo scripts
└── docs/                      # Documentation
```

## Testing

Before submitting:

```bash
# Test on small sample
python examples/test_small_scale.py --sample-size 20

# Verify core functionality
python examples/test_tagging.py
python examples/verify_all_refs_used.py
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test your changes
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

### PR Guidelines

- Clear title and description
- Reference related issues
- Include tests if applicable
- Update documentation if needed
- Keep changes focused (one feature/fix per PR)

## Areas for Contribution

### High Priority

- [ ] Cross-platform support (Linux, Windows tag detection)
- [ ] Unit tests for core modules
- [ ] CI/CD pipeline
- [ ] Performance optimizations

### Nice to Have

- [ ] Web interface
- [ ] Citation network analysis
- [ ] Multiple tag color support
- [ ] Export recommendations to CSV/JSON
- [ ] OCR support for scanned PDFs
- [ ] Topic clustering
- [ ] Incremental updates (only process new papers)

### Documentation

- [ ] Video tutorial
- [ ] More examples
- [ ] FAQ section
- [ ] Troubleshooting guide

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

## Questions?

- Open an issue with `[Question]` in title
- Join discussions on existing issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for helping improve Paper Recommender! 🙏

