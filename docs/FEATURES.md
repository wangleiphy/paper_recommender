# New Features: Smart Recommendations with Diversity

## 📊 Automatic 20% Recommendation

The system now **automatically recommends ~20% of your papers** by default!

### Your Collection:
- **Total papers**: 17,435
- **Red-tagged (references)**: 161
- **Candidates**: 17,274
- **Will recommend**: ~3,455 papers (20%)

### Why 20%?

This is a sweet spot that:
- ✅ Captures genuinely relevant papers
- ✅ Isn't overwhelming (not 80% of papers)
- ✅ Gives you a manageable reading list
- ✅ Can be adjusted with `--percent` flag

## 🎲 Surprise Factor (Diversity)

The new **surprise factor** adds variety to recommendations!

### How It Works:

**Without surprise (0.0)**:
- Pure similarity ranking
- Top 20% most similar papers
- Very predictable, safest choices

**Default (0.2 = 20%)**:
- 80% top similarity matches
- 20% "surprise" papers from next tier
- Good balance of relevance and discovery

**High surprise (0.5 = 50%)**:
- 50% top similarity matches
- 50% surprise papers
- Maximum variety, more hidden gems

### Example:

```bash
# Default: recommend 20% with 20% surprise
python recommend.py

# More surprises!
python recommend.py --surprise 0.3

# No surprises, pure similarity
python recommend.py --surprise 0

# Recommend 30% with 40% surprises
python recommend.py --percent 30 --surprise 0.4
```

## 🎯 What Are "Surprise" Papers?

Surprise papers are selected from ranks **beyond the top-k** but still relevant:

- **Top matches**: Ranked 1-10 (highest similarity)
- **Surprise pool**: Ranked 11-30 (still good, but overlooked)
- **Ignored**: Ranked 31+ (too different)

This means you get:
- Papers you'd definitely want (top matches)
- Papers you might not have noticed (surprises)
- Not random junk (still from top 3x range)

## 📈 Demo Results

From the diversity demo with 50 candidates:

### Surprise Factor: 0% (Pure Ranking)
1. Paper A - 0.6509 similarity
2. Paper B - 0.6099 similarity
3. Paper C - 0.5878 similarity
4. Paper D - 0.5862 similarity
5. Paper E - 0.5849 similarity

### Surprise Factor: 20% (Default)
1. Paper A - 0.6509 ← Top match (kept)
2. Paper C - 0.5878 ← Top match
3. Paper D - 0.5862 ← Top match
4. Paper B - 0.6099 ← Shuffled for variety
5. **Paper F - 0.5229** ← **Surprise!** (from rank 11-30)

### Surprise Factor: 50% (Maximum Variety)
1. Paper A - 0.6509 ← Top match (always kept)
2. Paper B - 0.6099 ← Top match
3. **Paper G - 0.5415** ← **Surprise!**
4. **Paper H - 0.5503** ← **Surprise!**
5. **Paper I - 0.5384** ← **Surprise!**

Notice:
- The #1 paper is always the same (best match)
- More surprises = more variety in results
- Surprises still have decent similarity (0.52-0.55)

## 🎨 Use Cases

### Conservative (Low Surprise)
```bash
python recommend.py --surprise 0.1
```
**Good for**: Finding papers very similar to your favorites

### Balanced (Default)
```bash
python recommend.py
# or
python recommend.py --surprise 0.2
```
**Good for**: General discovery with some variety

### Exploratory (High Surprise)
```bash
python recommend.py --surprise 0.4
```
**Good for**: Finding unexpected connections, broadening interests

## 🔧 All Options

```bash
# Basic: 20% of papers with 20% surprise
python recommend.py

# More papers
python recommend.py --percent 30

# Fewer papers
python recommend.py --percent 10

# Exact number
python recommend.py --top-k 100

# More variety
python recommend.py --surprise 0.3

# Pure similarity
python recommend.py --surprise 0

# Crazy variety!
python recommend.py --percent 25 --surprise 0.5
```

## 🎓 Technical Details

The diversity algorithm:
1. Computes average embedding from ALL 161 red-tagged papers
2. Ranks all candidates by cosine similarity
3. Selects top (1 - surprise_factor) from top rankings
4. Samples surprise_factor papers from next tier (rank k to 3k)
5. Shuffles slightly to mix top and surprises
6. Always keeps #1 paper (best match)

This ensures:
- Scientific rigor (similarity-based)
- Serendipitous discovery (surprise factor)
- Relevance (surprises from nearby ranks, not random)

