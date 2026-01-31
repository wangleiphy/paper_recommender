# Contributing

## Setup

```bash
git clone <repo>
cd paper-recommender
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Testing

```bash
python examples/test_small_scale.py --sample-size 50
```

## Code Style

- Follow PEP 8
- Add docstrings for public functions

## Pull Requests

1. Fork and create a feature branch
2. Test your changes
3. Submit PR with clear description

## License

MIT
