#!/usr/bin/env python3
"""
Demo script showing the new diversity/surprise features.
"""

import os
import sys
import random
from tqdm import tqdm

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector, PDFExtractor, SimilarityEngine


def demo_diversity():
    """Demo the diversity features with comparison."""
    
    print("=" * 70)
    print("Diversity & Surprise Factor Demo")
    print("=" * 70)
    print()
    
    source_dir = os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/')
    
    # Get papers
    print("Scanning...")
    all_pdfs = TagDetector.find_all_pdfs(source_dir, recursive=True)
    red_tagged = [pdf for pdf in all_pdfs if TagDetector.has_red_tag(pdf)][:10]  # Use 10 for demo
    non_tagged = [pdf for pdf in all_pdfs if not TagDetector.has_red_tag(pdf)]
    
    # Sample 50 candidates
    candidates = random.sample(non_tagged, min(50, len(non_tagged)))
    
    print(f"Using {len(red_tagged)} reference papers")
    print(f"Testing on {len(candidates)} candidate papers")
    print()
    
    # Extract text
    print("Extracting text...")
    reference_papers = []
    for pdf in tqdm(red_tagged):
        try:
            text = PDFExtractor.extract_text(pdf, max_pages=5)
            reference_papers.append({'path': pdf, 'text': text})
        except:
            pass
    
    candidate_papers = []
    for pdf in tqdm(candidates):
        try:
            text = PDFExtractor.extract_text(pdf, max_pages=5)
            metadata = PDFExtractor.extract_metadata(pdf)
            candidate_papers.append({
                'path': pdf,
                'text': text,
                'title': metadata['title'],
                'filename': metadata['filename']
            })
        except:
            pass
    
    print()
    
    # Get embeddings
    engine = SimilarityEngine()
    reference_embeddings = []
    for paper in reference_papers:
        embedding = engine.get_embedding(paper['text'], paper['path'])
        reference_embeddings.append(embedding)
    
    # Calculate 20% recommendation count
    num_to_recommend = max(5, int(len(candidate_papers) * 0.20))
    
    print("=" * 70)
    print(f"Recommending {num_to_recommend} papers (~20% of {len(candidate_papers)} candidates)")
    print("=" * 70)
    print()
    
    # Test different surprise factors
    for surprise_factor in [0.0, 0.2, 0.5]:
        print(f"\n{'─' * 70}")
        print(f"Surprise Factor: {surprise_factor:.0%}")
        print(f"{'─' * 70}")
        
        if surprise_factor == 0.0:
            print("(Pure similarity-based ranking)")
        elif surprise_factor == 0.2:
            print("(80% top matches + 20% surprises)")
        elif surprise_factor == 0.5:
            print("(50% top matches + 50% surprises - maximum variety!)")
        print()
        
        recommendations = engine.find_similar_papers_with_diversity(
            reference_embeddings,
            candidate_papers,
            top_k=min(5, num_to_recommend),  # Show top 5 for demo
            surprise_factor=surprise_factor
        )
        
        for i, (paper, score) in enumerate(recommendations, 1):
            print(f"{i}. {paper['title'][:60]}")
            print(f"   Similarity: {score:.4f}")
            print()
    
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print()
    print("✓ Lower surprise factor (0.0-0.2): More predictable, highest similarity")
    print("✓ Higher surprise factor (0.3-0.5): More variety, includes hidden gems")
    print()
    print("Default recommendation: 20% of candidates with 20% surprise factor")
    print(f"For your collection: ~{int(len(non_tagged) * 0.20):,} papers will be recommended")
    print()


if __name__ == '__main__':
    demo_diversity()

