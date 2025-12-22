# Quick Start Guide 🚀

Get started with Paper Recommender in 5 minutes!

## Step 1: Installation (2 minutes)

```bash
# Clone and enter directory
cd paper_recommender

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Tag Your Favorites (1 minute)

1. Open Finder
2. Navigate to your papers (e.g., Downloads)
3. Select 5-10 papers you like
4. Right-click → **Tags** → **Red**

**Pro tip**: Hold ⌘ to select multiple files at once!

## Step 3: Run Recommender (2 minutes)

```bash
# Quick test on 1000 random papers
python scripts/recommend.py --subsample 1000

# Or process all papers (slower first time)
# python scripts/recommend.py
```

That's it! The system will:
- ✅ Find all red-tagged papers
- ✅ Extract text from them
- ✅ Compute similarity with all other papers
- ✅ Recommend ~20% of papers
- ✅ Tag recommendations with green

## Step 4: Find Your Recommendations

In Finder:
1. Navigate to your papers folder
2. Filter by tag: **Green**
3. See all recommended papers!

## What's Next?

### Test on Small Sample First

```bash
# Try on just 100 papers to get a feel for it
python examples/test_small_scale.py --sample-size 100
```

### Adjust Settings

```bash
# Sample more papers
python scripts/recommend.py --subsample 2000

# More recommendations
python scripts/recommend.py --subsample 1000 --percent 30

# More variety/surprises
python scripts/recommend.py --subsample 1000 --surprise 0.3

# Conservative (less variety)
python scripts/recommend.py --subsample 500 --percent 15 --surprise 0.1

# Process all papers (no sampling)
python scripts/recommend.py
```

### Explore Examples

```bash
# See diversity in action
python examples/demo_diversity.py

# Estimate full run time/cost
python examples/estimate_cost.py
```

## Common Issues

### "No red-tagged PDFs found"
→ Make sure you tagged some PDFs with red in Finder!

### "ModuleNotFoundError"
→ Activate the virtual environment: `source venv/bin/activate`

### First run is slow
→ Normal! It extracts/embeds all papers. Subsequent runs are fast (cached).

## Understanding the Output

```
[1/4] Scanning directory: /path/to/Downloads
  Found 17435 total PDF files
  Found 161 red-tagged PDF files
```
→ Found your tagged favorites

```
[2/4] Extracting text from ALL 161 red-tagged papers...
  Successfully extracted text from 159/161 papers
```
→ Reading your favorites (some may fail if they're scanned images)

```
[3/4] Extracting text from candidate papers...
  Successfully extracted text from 17200/17274 papers
```
→ Reading all other papers

```
[4/4] Computing similarities and generating recommendations...
  Will recommend 3455 papers (~20.0% of 17274 candidates)
  Surprise factor: 20% (adds variety to recommendations)
```
→ Computing similarity and ranking

```
Tagging Recommendations with Green Tag
Successfully tagged 3455/3455 papers
```
→ Marking recommendations in Finder

## Tips for Best Results

1. **Tag diverse favorites**: Tag papers from different sub-topics you're interested in
2. **Tag quality over quantity**: 10-20 good examples is better than 100 random ones
3. **Start with 20%**: The default 20% recommendation is usually a good sweet spot
4. **Use surprise factor**: Default 20% adds nice variety without going overboard
5. **Re-run when you add favorites**: Tag more papers, run again to update recommendations

## Full Documentation

- [README.md](README.md) - Complete documentation
- [docs/FEATURES.md](docs/FEATURES.md) - Feature details
- [docs/USAGE_NOTES.md](docs/USAGE_NOTES.md) - Usage tips

Enjoy discovering papers! 📚✨

