#!/usr/bin/env python3
"""
Estimate time and cost for full paper recommendation run.
"""

def estimate_full_run(total_pdfs=17435, red_tagged=160):
    """
    Estimate time and cost based on test run performance.
    """
    print("=" * 70)
    print("Full Run Estimation")
    print("=" * 70)
    print()
    
    # Data from test run of 100 papers
    test_papers = 100
    test_extraction_time = 8  # seconds (4s for red-tagged + 4s for candidates)
    test_embedding_time = 27  # seconds for 50 papers
    
    # Calculate rates
    extraction_rate = test_papers / test_extraction_time  # papers/second
    embedding_rate = 50 / test_embedding_time  # papers/second
    
    print(f"Dataset Statistics:")
    print(f"  Total PDFs: {total_pdfs:,}")
    print(f"  Red-tagged (reference): {red_tagged}")
    print(f"  Non-tagged (candidates): {total_pdfs - red_tagged:,}")
    print()
    
    print(f"Performance Metrics (from test run):")
    print(f"  Text extraction: {extraction_rate:.1f} papers/second")
    print(f"  Embedding generation: {embedding_rate:.2f} papers/second")
    print()
    
    # Time estimation
    print("=" * 70)
    print("TIME ESTIMATION")
    print("=" * 70)
    print()
    
    # 1. Text extraction for all papers
    extraction_time = total_pdfs / extraction_rate
    extraction_minutes = extraction_time / 60
    
    print(f"1. Text Extraction (all {total_pdfs:,} papers):")
    print(f"   {extraction_minutes:.1f} minutes ({extraction_time/3600:.1f} hours)")
    print()
    
    # 2. Embedding generation (first run only)
    # Note: Subsequent runs will be cached
    embedding_time = total_pdfs / embedding_rate
    embedding_minutes = embedding_time / 60
    
    print(f"2. Embedding Generation (first run, all {total_pdfs:,} papers):")
    print(f"   {embedding_minutes:.1f} minutes ({embedding_time/3600:.1f} hours)")
    print()
    
    # 3. Similarity computation (very fast, negligible)
    similarity_time = 5  # seconds, very fast
    
    print(f"3. Similarity Computation:")
    print(f"   ~{similarity_time} seconds (negligible)")
    print()
    
    # Total time
    total_time = extraction_time + embedding_time + similarity_time
    total_minutes = total_time / 60
    total_hours = total_time / 3600
    
    print("-" * 70)
    print(f"FIRST RUN (with model download):")
    print(f"  Model download: ~2-3 minutes (one-time, ~90MB)")
    print(f"  Processing: {total_minutes:.0f} minutes ({total_hours:.1f} hours)")
    print(f"  TOTAL: ~{total_hours:.1f} hours")
    print()
    
    # Subsequent runs (only new papers)
    print(f"SUBSEQUENT RUNS (with cache):")
    print(f"  Only processes papers not in cache")
    print(f"  If 100 new papers added: ~5-10 minutes")
    print(f"  If re-running on same papers: ~2-3 minutes (cache hit)")
    print()
    
    # Cost estimation
    print("=" * 70)
    print("COST ESTIMATION")
    print("=" * 70)
    print()
    
    print("Software Costs:")
    print("  ✓ All models are LOCAL (no API costs)")
    print("  ✓ Sentence-BERT runs on your computer")
    print("  ✓ No OpenAI/Anthropic/Cloud API calls")
    print("  ✓ Total software cost: $0.00")
    print()
    
    print("Computational Costs (electricity):")
    # Assume M2 MacBook Pro power consumption
    # Active: ~30W average for ML tasks
    # Electricity: ~$0.15/kWh (US average)
    power_watts = 30
    power_kwh = power_watts / 1000
    cost_per_kwh = 0.15
    
    energy_kwh = (total_time / 3600) * power_kwh
    electricity_cost = energy_kwh * cost_per_kwh
    
    print(f"  Power consumption: ~{power_watts}W (ML workload on M2 Mac)")
    print(f"  Runtime: {total_hours:.1f} hours")
    print(f"  Energy: {energy_kwh:.3f} kWh")
    print(f"  Electricity cost: ${electricity_cost:.2f} (at $0.15/kWh)")
    print()
    
    print("Total Cost:")
    print(f"  💰 ${electricity_cost:.2f} (just electricity)")
    print()
    
    # Optimizations
    print("=" * 70)
    print("OPTIMIZATION STRATEGIES")
    print("=" * 70)
    print()
    
    print("To speed up processing:")
    print()
    print("1. Process in batches:")
    print("   python test_small_scale.py --sample-size 1000")
    print("   (Build up cache gradually)")
    print()
    
    print("2. Reduce max_pages in pdf_extractor.py:")
    print("   Currently: 10 pages per paper")
    print("   Reduce to 5: ~50% faster extraction")
    print()
    
    print("3. Run overnight:")
    print("   Start before bed, results ready in morning")
    print()
    
    print("4. Filter by date/folder:")
    print("   Only process papers from last year")
    print()
    
    # Comparison to API-based approaches
    print("=" * 70)
    print("COMPARISON: API-Based Approaches")
    print("=" * 70)
    print()
    
    print("If using OpenAI Embeddings API instead:")
    # text-embedding-3-small: $0.020 per 1M tokens
    # Average paper ~5000 tokens
    avg_tokens_per_paper = 5000
    total_tokens = total_pdfs * avg_tokens_per_paper
    openai_cost = (total_tokens / 1_000_000) * 0.020
    
    print(f"  Model: text-embedding-3-small")
    print(f"  Cost: $0.020 per 1M tokens")
    print(f"  Estimated tokens: {total_tokens:,}")
    print(f"  Total cost: ${openai_cost:.2f}")
    print()
    
    print("✓ Local approach saves: ${:.2f}".format(openai_cost - electricity_cost))
    print()
    
    print("=" * 70)


if __name__ == '__main__':
    estimate_full_run()

