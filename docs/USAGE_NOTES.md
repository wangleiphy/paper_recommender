# Usage Notes

## How Recommendations Work

### Reference Papers (Red-Tagged)

**The system ALWAYS uses ALL red-tagged papers as references - no sampling!**

- ✅ All 160+ red-tagged papers in your collection are processed
- ✅ Embeddings are computed for every red-tagged paper
- ✅ The average embedding represents your complete preferences
- ✅ This ensures recommendations capture the full breadth of your interests

### Why Use All Red-Tagged Papers?

1. **Comprehensive Coverage**: Your interests likely span multiple topics. Using all papers ensures recommendations cover all areas.

2. **Better Quality**: More reference papers = more robust similarity computation

3. **No Bias**: No sampling means no risk of accidentally excluding important reference papers

### Performance Impact

With your 161 red-tagged papers:
- **First run**: ~6 minutes to process all red-tagged papers
- **Subsequent runs**: ~10 seconds (embeddings are cached!)
- **Cache location**: `.cache/embeddings_cache.pkl`

### Example Output

```
[2/4] Extracting text from ALL 161 red-tagged papers...
  Successfully extracted text from 159/161 papers

[4/4] Computing similarities and generating recommendations...
  Processing reference papers: 100%|██████████| 159/159
```

## Recommendation Quality

The system computes an **average embedding** from all your red-tagged papers:

```python
avg_reference_embedding = np.mean(reference_embeddings, axis=0)
```

Then finds papers with highest cosine similarity to this average, effectively finding papers that are similar to your "average interest profile."

## Alternative Approaches (Not Implemented)

If you want different behavior in the future, consider:

1. **Topic Clustering**: Group red-tagged papers by topic, recommend based on each cluster
2. **Maximum Similarity**: Recommend papers similar to ANY red-tagged paper (not average)
3. **Weighted Average**: Weight more recently tagged papers higher
4. **Tag-Specific**: Add support for multiple colored tags with different purposes

## Verifying Behavior

Run this to see exactly how many papers are being used:

```bash
python recommend.py --verbose
```

You'll see clear output showing:
- Total red-tagged papers found
- Number successfully processed
- All papers are used (no "[1/10]" or sampling indicators)

