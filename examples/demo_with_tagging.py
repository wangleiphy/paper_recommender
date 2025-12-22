#!/usr/bin/env python3
"""
Demo script to show the recommendation system with green tagging.
This will process a small sample and tag the recommendations.
"""

import os
import sys
import random
from tqdm import tqdm

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector, PDFExtractor, SimilarityEngine


def demo_recommendation_with_tagging(source_dir: str, num_candidates: int = 10):
    """
    Demo the recommendation system with green tagging on a small sample.
    
    Args:
        source_dir: Directory to scan
        num_candidates: Number of candidate papers to consider
    """
    print("=" * 70)
    print("Paper Recommender - Demo with Green Tagging")
    print("=" * 70)
    print()
    
    # Find papers
    print(f"Scanning: {source_dir}")
    all_pdfs = TagDetector.find_all_pdfs(source_dir, recursive=True)
    red_tagged = [pdf for pdf in all_pdfs if TagDetector.has_red_tag(pdf)]
    non_tagged = [pdf for pdf in all_pdfs if not TagDetector.has_red_tag(pdf)]
    
    print(f"  Total: {len(all_pdfs):,} PDFs")
    print(f"  Red-tagged: {len(red_tagged)}")
    print(f"  Non-tagged: {len(non_tagged):,}")
    print()
    
    if len(red_tagged) == 0:
        print("No red-tagged papers found!")
        return 1
    
    # Sample candidates
    if len(non_tagged) > num_candidates:
        print(f"Sampling {num_candidates} random candidates...")
        candidates = random.sample(non_tagged, num_candidates)
    else:
        candidates = non_tagged
    
    print()
    
    # Extract text from ALL red-tagged papers
    print(f"Extracting text from ALL {len(red_tagged)} reference papers...")
    reference_papers = []
    for pdf in tqdm(red_tagged):  # Use ALL red-tagged papers
        try:
            text = PDFExtractor.extract_text(pdf, max_pages=10)
            reference_papers.append({'path': pdf, 'text': text})
        except:
            pass
    
    print(f"Extracted {len(reference_papers)}/{len(red_tagged)} reference papers")
    print()
    
    # Extract text from candidates
    print("Extracting text from candidate papers...")
    candidate_papers = []
    for pdf in tqdm(candidates):
        try:
            text = PDFExtractor.extract_text(pdf, max_pages=10)
            metadata = PDFExtractor.extract_metadata(pdf)
            candidate_papers.append({
                'path': pdf,
                'text': text,
                'title': metadata['title'],
                'filename': metadata['filename']
            })
        except:
            pass
    
    print(f"Extracted {len(candidate_papers)} candidate papers")
    print()
    
    # Compute similarities
    print("Computing similarities...")
    engine = SimilarityEngine()
    
    reference_embeddings = []
    for paper in tqdm(reference_papers, desc="Reference embeddings"):
        embedding = engine.get_embedding(paper['text'], paper['path'])
        reference_embeddings.append(embedding)
    
    recommendations = engine.find_similar_papers(
        reference_embeddings,
        candidate_papers,
        top_k=3
    )
    
    print()
    print("=" * 70)
    print(f"Top {len(recommendations)} Recommendations:")
    print("=" * 70)
    print()
    
    for i, (paper, score) in enumerate(recommendations, 1):
        print(f"{i}. {paper['title']}")
        print(f"   Similarity: {score:.4f}")
        print(f"   File: {paper['filename']}")
        print()
    
    # Tag recommendations
    print("=" * 70)
    print("Tagging Recommendations with Green Tag")
    print("=" * 70)
    print()
    
    for i, (paper, score) in enumerate(recommendations, 1):
        print(f"Tagging: {paper['filename']}", end=" ... ")
        success = TagDetector.add_green_tag(paper['path'])
        if success:
            print("✓")
        else:
            print("✗")
    
    print()
    print("=" * 70)
    print("✓ Demo Complete!")
    print("=" * 70)
    print()
    print("Check Finder to see the green 'Recommended' tags on:")
    for paper, score in recommendations:
        print(f"  - {paper['filename']}")
    print()
    
    return 0


if __name__ == '__main__':
    source = os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/')
    exit(demo_recommendation_with_tagging(source, num_candidates=20))

