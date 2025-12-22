# Documentation

Detailed documentation for the paper recommender system.

## Files

### `FEATURES.md`
Comprehensive documentation of all features including:
- Smart 20% recommendation system
- Surprise factor and diversity
- Technical details and algorithms
- Use cases and examples

### `USAGE_NOTES.md`
Practical usage notes covering:
- How recommendations work
- Why all red-tagged papers are used
- Performance characteristics
- Alternative approaches

## Key Concepts

### Reference Papers
All red-tagged papers in your collection. The system uses **ALL** of them to understand your preferences.

### Candidate Papers
Non-tagged papers that will be ranked for recommendations.

### Similarity Score
Cosine similarity between embeddings (0.0 to 1.0). Higher = more similar.

### Surprise Factor
Percentage of recommendations from "next tier" instead of pure top matches. Adds variety and discovery.

### Recommendation Percentage
What portion of candidates to recommend. Default is 20% - a good balance between coverage and manageability.

## Quick Reference

### Default Behavior
- Uses ALL red-tagged papers as references
- Recommends 20% of candidates
- 20% surprise factor for variety
- Auto-tags recommendations with green

### Adjustable Parameters
- `--percent`: Recommendation percentage (5-50% typical)
- `--surprise`: Diversity factor (0.0-0.5 typical)
- `--top-k`: Exact number instead of percentage
- `--no-tag`: Skip auto-tagging

### Performance
- First run: ~3 hours for 17K papers
- Subsequent: ~10 seconds (cached)
- Cost: Essentially free (local processing)

