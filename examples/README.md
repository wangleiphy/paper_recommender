# Examples

This directory contains example scripts and demos for the paper recommender system.

## Scripts

### `demo_diversity.py`
Demonstrates the diversity/surprise feature with comparison of different surprise factors.

```bash
python examples/demo_diversity.py
```

Shows recommendations with 0%, 20%, and 50% surprise factors side-by-side.

### `demo_with_tagging.py`
Full demo showing the complete workflow including Gray tagging of recommendations.

```bash
python examples/demo_with_tagging.py
```

Processes a small sample and applies Gray tags to top recommendations.

### `test_small_scale.py`
Tests the system on a random sample of papers (default: 100).

```bash
python examples/test_small_scale.py --sample-size 100 --top-k 5
```

Options:
- `--source DIR`: Source directory (default: iCloud Downloads)
- `--sample-size N`: Number of papers to sample
- `--top-k N`: Number of recommendations
- `--keep-temp`: Keep temporary directory after test

### `test_tagging.py`
Simple test to verify Gray tagging functionality works.

```bash
python examples/test_tagging.py
```

Tags one test file and verifies the tag appears.

### `verify_all_refs_used.py`
Verifies that ALL red-tagged papers are used as references.

```bash
python examples/verify_all_refs_used.py
```

Shows statistics and confirms no sampling of reference papers.

### `estimate_cost.py`
Estimates time and cost for running on full collection.

```bash
python examples/estimate_cost.py
```

Provides estimates for:
- Total processing time
- Electricity cost
- Comparison with cloud APIs

## Usage Tips

1. **Start small**: Try `test_small_scale.py` first
2. **Check diversity**: Run `demo_diversity.py` to understand surprise factor
3. **Verify tagging**: Use `test_tagging.py` to ensure tags work
4. **Plan ahead**: Run `estimate_cost.py` before full-scale processing

