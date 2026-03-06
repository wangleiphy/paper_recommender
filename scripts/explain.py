#!/usr/bin/env python3
"""
Explain why a paper was recommended by showing per-reference similarity scores.

Usage:
  python scripts/explain.py "Machine Learning the Strong Disorder"
  python scripts/explain.py 2603.12345
"""

import os
import sys
import argparse
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector, SimilarityEngine, ArxivClient, paper_to_dict
from paper_recommender.utils import extract_paper_data

DEFAULT_DIRECTORY = os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/')
DEFAULT_AUTHOR_ID = 'wang_l_1'
DEFAULT_ARXIV_CATEGORIES = [
    'cs.LG', 'stat.ML', 'cond-mat',
    'physics.comp-ph', 'physics.chem-ph', 'quant-ph',
]


def main():
    parser = argparse.ArgumentParser(description='Explain a paper recommendation')
    parser.add_argument('query', help='Paper title substring or arXiv ID to explain')
    parser.add_argument('--directory', '-d', default=DEFAULT_DIRECTORY)
    parser.add_argument('--top-refs', '-n', type=int, default=10,
                        help='Show top N most similar references (default: 10)')
    parser.add_argument('--model', '-m', default='all-mpnet-base-v2')
    parser.add_argument('--refs', default='both', choices=['author', 'tagged', 'both'])
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    engine = SimilarityEngine(model_name=args.model)

    # Gather reference papers
    reference_papers = []

    if args.refs in ('tagged', 'both'):
        directory = os.path.expanduser(args.directory)
        red_tagged = TagDetector.find_red_tagged_pdfs(directory, recursive=True)
        print(f"Found {len(red_tagged)} red-tagged papers")
        for pdf_path in red_tagged:
            paper_data = extract_paper_data(pdf_path, verbose=args.verbose)
            if paper_data:
                reference_papers.append(paper_data)

    if args.refs in ('author', 'both'):
        client = ArxivClient()
        author_papers = client.get_author_papers(DEFAULT_AUTHOR_ID, verbose=args.verbose)
        print(f"Found {len(author_papers)} author papers")
        for p in author_papers:
            reference_papers.append(paper_to_dict(p))

    print(f"Total references: {len(reference_papers)}")
    print()

    # Find the target paper
    print(f"Searching for: {args.query}")
    client = ArxivClient()

    # Check if query looks like an arXiv ID (e.g., 2603.05164 or 2603.05164v1)
    import re
    target = None
    if re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', args.query):
        # Direct lookup by arXiv ID
        papers = client.fetch_by_ids([args.query], verbose=args.verbose)
        if papers:
            target = paper_to_dict(papers[0])
    else:
        # Search by title
        papers = client.search(query=args.query, max_results=10, days_back=None)
        query_lower = args.query.lower()
        for p in papers:
            if query_lower in p['title'].lower():
                target = paper_to_dict(p)
                break
        # If no substring match, take the top result
        if not target and papers:
            target = paper_to_dict(papers[0])

    if not target:
        print(f"Could not find paper matching '{args.query}'")
        return 1

    print(f"Found: {target['title']}")
    print(f"  arXiv ID: {target['arxiv_id']}")
    print(f"  Authors: {target['author']}")
    print()

    # Compute target embedding
    target_embedding = engine.get_embedding(target['text'], target['path'])

    # Compute per-reference similarities
    ref_scores = []
    for ref in reference_papers:
        ref_embedding = engine.get_embedding(ref['text'], ref['path'])
        sim = engine.compute_similarity(ref_embedding, target_embedding)
        ref_scores.append((ref, float(sim)))

    ref_scores.sort(key=lambda x: x[1], reverse=True)

    # Also compute similarity to the average (what the system actually uses)
    all_ref_embeddings = [engine.get_embedding(r['text'], r['path']) for r in reference_papers]
    avg_embedding = np.mean(all_ref_embeddings, axis=0)
    avg_sim = engine.compute_similarity(avg_embedding, target_embedding)

    print("=" * 70)
    print(f"Similarity to average reference (what the system uses): {avg_sim:.4f}")
    print("=" * 70)
    print()

    # Show top similar references
    n = min(args.top_refs, len(ref_scores))
    print(f"Top {n} most similar reference papers:")
    print("-" * 70)
    for i, (ref, score) in enumerate(ref_scores[:n], 1):
        title = ref.get('title', ref.get('filename', ref.get('path', '?')))
        source = "author" if ref['path'] and not ref['path'].startswith('/') else "tagged"
        print(f"{i:3d}. [{score:.4f}] ({source}) {title}")
    print()

    # Show bottom references too
    print(f"Bottom {min(3, len(ref_scores))} least similar references:")
    print("-" * 70)
    for ref, score in ref_scores[-3:]:
        title = ref.get('title', ref.get('filename', ref.get('path', '?')))
        source = "author" if ref['path'] and not ref['path'].startswith('/') else "tagged"
        print(f"     [{score:.4f}] ({source}) {title}")
    print()

    # Summary stats
    all_sims = [s for _, s in ref_scores]
    print(f"Reference similarity stats:")
    print(f"  Mean:   {np.mean(all_sims):.4f}")
    print(f"  Median: {np.median(all_sims):.4f}")
    print(f"  Std:    {np.std(all_sims):.4f}")
    print(f"  Min:    {np.min(all_sims):.4f}")
    print(f"  Max:    {np.max(all_sims):.4f}")


if __name__ == '__main__':
    exit(main())
