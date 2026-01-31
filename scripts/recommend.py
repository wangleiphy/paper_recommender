#!/usr/bin/env python3
"""
Paper Recommender - Find papers similar to your favorites.

Two modes:
  local  - Recommend from your local PDF collection
  arxiv  - Recommend from recent arXiv preprints

Usage:
  python recommend.py local [options]
  python recommend.py arxiv [options]
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector, SimilarityEngine, ArxivClient, paper_to_dict
from paper_recommender.utils import extract_paper_data, move_files_with_pattern


# Default paths
DEFAULT_DIRECTORY = os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/')
DEFAULT_DUPLICATE_TARGET = '/Users/lewang/Library/CloudStorage/OneDrive-Personal/文档'

# Default arXiv categories - ML/AI + Physics
DEFAULT_ARXIV_CATEGORIES = [
    'cs.LG', 'stat.ML',           # Machine Learning
    'cond-mat',                   # All Condensed Matter
    'physics.comp-ph',            # Computational Physics
    'physics.chem-ph',            # Chemical Physics
    'quant-ph',                   # Quantum Physics
]


def get_reference_papers(directory: str, recursive: bool, verbose: bool) -> tuple:
    """Find and extract text from red-tagged reference papers."""
    print(f"Scanning for red-tagged papers: {directory}")
    red_tagged_pdfs = TagDetector.find_red_tagged_pdfs(directory, recursive=recursive)
    print(f"  Found {len(red_tagged_pdfs)} red-tagged PDF files")
    print()

    if len(red_tagged_pdfs) == 0:
        print("No red-tagged PDF files found!")
        print("Please tag some papers with a red tag in Finder and try again.")
        return [], []

    # Show red-tagged papers
    print("Reference papers:")
    for pdf_path in red_tagged_pdfs:
        print(f"  ✓ {os.path.basename(pdf_path)}")
    print()

    # Extract text
    print(f"Extracting text from {len(red_tagged_pdfs)} reference papers...")
    reference_papers = []
    for pdf_path in tqdm(red_tagged_pdfs, disable=not verbose):
        paper_data = extract_paper_data(pdf_path, verbose=verbose)
        if paper_data:
            reference_papers.append(paper_data)

    print(f"  Successfully extracted text from {len(reference_papers)}/{len(red_tagged_pdfs)} papers")
    print()

    return red_tagged_pdfs, reference_papers


def get_reference_embeddings(reference_papers: List[Dict], engine: SimilarityEngine, verbose: bool) -> List:
    """Get embeddings for reference papers."""
    reference_embeddings = []
    for paper in tqdm(reference_papers, desc="  Encoding references", disable=not verbose):
        embedding = engine.get_embedding(paper['text'], paper['path'])
        reference_embeddings.append(embedding)
    return reference_embeddings


def print_recommendations(recommendations: List, mode: str = "local"):
    """Print recommendation results."""
    print()
    print("=" * 70)
    title = "Recommended Papers" if mode == "local" else "Recommended arXiv Papers"
    print(f"Top {len(recommendations)} {title}:")
    print("=" * 70)
    print()

    for i, (paper, score) in enumerate(recommendations, 1):
        print(f"{i}. {paper['title']}")
        print(f"   Similarity: {score:.4f}")

        if mode == "arxiv":
            print(f"   arXiv ID: {paper.get('arxiv_id', 'N/A')}")
            print(f"   Authors: {paper.get('author', 'N/A')}")
            if paper.get('categories'):
                print(f"   Categories: {', '.join(paper['categories'][:3])}")
            if paper.get('published'):
                print(f"   Published: {paper['published'].strftime('%Y-%m-%d')}")
        else:
            print(f"   File: {paper['filename']}")
            if paper['author']:
                print(f"   Author: {paper['author']}")
        print()


def recommend_local(
    directory: str,
    top_k: int = 10,
    verbose: bool = False,
    recursive: bool = True,
    tag_recommendations: bool = True,
    surprise_factor: float = 0.2,
    max_candidates: Optional[int] = None,
    move_duplicates: bool = True,
    duplicate_target_dir: Optional[str] = None
):
    """Recommend papers from local collection."""
    print("=" * 70)
    print("Paper Recommender - Local Mode")
    print("=" * 70)
    print()

    # Step 1: Find red-tagged and all PDFs
    print("[1/4] Finding papers...")
    red_tagged_pdfs, reference_papers = get_reference_papers(directory, recursive, verbose)

    if not reference_papers:
        return

    all_pdfs = TagDetector.find_all_pdfs(directory, recursive=recursive)
    print(f"  Found {len(all_pdfs)} total PDF files")
    print()

    if len(all_pdfs) == len(red_tagged_pdfs):
        print("All PDFs are red-tagged. No papers to recommend.")
        return

    # Step 2: Get candidate papers
    candidate_pdfs = [pdf for pdf in all_pdfs if pdf not in red_tagged_pdfs]

    if max_candidates and max_candidates < len(candidate_pdfs):
        import random
        print(f"[2/4] Sampling {max_candidates} from {len(candidate_pdfs):,} candidates...")
        candidate_pdfs = random.sample(candidate_pdfs, max_candidates)
    else:
        print(f"[2/4] Processing {len(candidate_pdfs):,} candidate papers...")

    candidate_papers = []
    for pdf_path in tqdm(candidate_pdfs, disable=not verbose):
        paper_data = extract_paper_data(pdf_path, verbose=verbose)
        if paper_data:
            candidate_papers.append(paper_data)

    print(f"  Extracted text from {len(candidate_papers)}/{len(candidate_pdfs)} papers")
    print()

    if not candidate_papers:
        print("No candidate papers to compare!")
        return

    # Cap top_k at available papers
    top_k = min(top_k, len(candidate_papers))

    # Step 3: Compute similarities
    print(f"[3/4] Computing similarities...")
    print(f"  Will recommend {top_k} papers from {len(candidate_papers)} candidates")
    print()

    engine = SimilarityEngine()
    reference_embeddings = get_reference_embeddings(reference_papers, engine, verbose)

    recommendations = engine.find_similar_papers_with_diversity(
        reference_embeddings,
        candidate_papers,
        top_k=top_k,
        surprise_factor=surprise_factor
    )

    print_recommendations(recommendations, mode="local")

    # Step 4: Tag recommendations
    if tag_recommendations:
        print("[4/4] Tagging recommendations...")
        tagged_count = 0
        for paper, score in recommendations:
            if TagDetector.add_green_tag(paper['path']):
                Path(paper['path']).touch()
                tagged_count += 1
                if verbose:
                    print(f"  ✓ Tagged: {paper['filename']}")

        print(f"  Tagged {tagged_count}/{len(recommendations)} papers with Gray")

        # Move duplicates
        if move_duplicates:
            target = duplicate_target_dir or DEFAULT_DUPLICATE_TARGET
            file_paths = [paper['path'] for paper, _ in recommendations]
            moved = move_files_with_pattern(file_paths, target, verbose=verbose)
            if moved > 0:
                print(f"  Moved {moved} duplicate files to: {target}")

    print()
    print("=" * 70)
    print("✓ Done!")
    print("=" * 70)


def recommend_arxiv(
    reference_directory: str,
    output_directory: str,
    categories: Optional[List[str]] = None,
    max_candidates: int = 100,
    days: int = 7,
    top_k: int = 10,
    verbose: bool = False,
    recursive: bool = True,
    tag_recommendations: bool = True,
    download: bool = True,
    surprise_factor: float = 0.2,
):
    """Recommend papers from arXiv."""
    if categories is None:
        categories = DEFAULT_ARXIV_CATEGORIES

    print("=" * 70)
    print("Paper Recommender - arXiv Mode")
    print("=" * 70)
    print()

    # Step 1: Get reference papers
    print("[1/5] Finding reference papers...")
    _, reference_papers = get_reference_papers(reference_directory, recursive, verbose)

    if not reference_papers:
        return

    # Step 2: Fetch from arXiv
    print(f"[2/5] Fetching from arXiv...")
    print(f"  Categories: {', '.join(categories)}")
    print(f"  Last {days} days, max {max_candidates} papers")
    print()

    client = ArxivClient()
    arxiv_papers = client.get_recent_papers(
        categories=categories,
        max_results=max_candidates,
        days_back=days,
        verbose=verbose
    )

    print(f"  Retrieved {len(arxiv_papers)} papers")
    print()

    if not arxiv_papers:
        print("No papers found on arXiv!")
        return

    candidate_papers = [paper_to_dict(p) for p in arxiv_papers]

    # Step 3: Compute similarities
    print(f"[3/5] Computing similarities...")
    top_k = min(top_k, len(candidate_papers))
    print(f"  Will recommend {top_k} papers")
    print()

    engine = SimilarityEngine()
    reference_embeddings = get_reference_embeddings(reference_papers, engine, verbose)

    recommendations = engine.find_similar_papers_with_diversity(
        reference_embeddings,
        candidate_papers,
        top_k=top_k,
        surprise_factor=surprise_factor
    )

    print_recommendations(recommendations, mode="arxiv")

    # Step 4: Download
    if download:
        print("[4/5] Downloading papers...")
        print(f"  Output: {output_directory}")
        os.makedirs(output_directory, exist_ok=True)

        downloaded = []
        for paper, score in tqdm(recommendations, desc="  Downloading"):
            arxiv_id = paper.get('arxiv_id', '')
            original = next((p for p in arxiv_papers if p['arxiv_id'] == arxiv_id), None)
            if original:
                pdf_path = client.download_pdf(original, output_directory, verbose=verbose)
                if pdf_path:
                    downloaded.append((pdf_path, paper, score))

        print(f"  Downloaded {len(downloaded)}/{len(recommendations)} papers")
        print()

        # Step 5: Tag
        if tag_recommendations and downloaded:
            print("[5/5] Tagging papers...")
            tagged = 0
            for pdf_path, paper, score in downloaded:
                if TagDetector.add_green_tag(pdf_path):
                    Path(pdf_path).touch()
                    tagged += 1
                    if verbose:
                        print(f"  ✓ Tagged: {os.path.basename(pdf_path)}")
            print(f"  Tagged {tagged}/{len(downloaded)} papers with Gray")

    print()
    print("=" * 70)
    print("✓ Done!")
    print("=" * 70)


def add_common_args(parser):
    """Add arguments common to both modes."""
    parser.add_argument(
        '--directory', '-d', default=DEFAULT_DIRECTORY,
        help='Directory with papers (default: iCloud Downloads)'
    )
    parser.add_argument(
        '--top-k', '-k', type=int, default=10,
        help='Number of papers to recommend (default: 10)'
    )
    parser.add_argument(
        '--max-candidates', '-n', type=int, default=None,
        help='Max candidate papers to consider (default: all for local, 100 for arxiv)'
    )
    parser.add_argument(
        '--surprise', '-s', type=float, default=0.2,
        help='Diversity factor 0-1, higher=more variety (default: 0.2)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--no-recursive', action='store_true',
        help='Don\'t search subdirectories'
    )
    parser.add_argument(
        '--no-tag', action='store_true',
        help='Don\'t tag recommendations with Gray'
    )


def main():
    """Main entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description='Recommend papers similar to your red-tagged favorites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  local   Find similar papers in your local PDF collection
  arxiv   Discover new papers from recent arXiv preprints

Examples:
  python recommend.py local                      # Local recommendations
  python recommend.py local -k 20 -n 1000        # Top 20 from 1000 sampled
  python recommend.py arxiv                      # arXiv recommendations
  python recommend.py arxiv -k 20 --days 14      # Top 20 from last 2 weeks
        """
    )

    subparsers = parser.add_subparsers(dest='mode', help='Recommendation mode')

    # ==================== LOCAL subcommand ====================
    local_parser = subparsers.add_parser(
        'local',
        help='Recommend from local PDF collection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python recommend.py local                 # Recommend 10 papers
  python recommend.py local -k 50           # Recommend 50 papers
  python recommend.py local -n 1000         # Sample 1000 candidates first (faster)
  python recommend.py local -k 20 -n 500    # Top 20 from 500 sampled candidates
        """
    )
    add_common_args(local_parser)
    local_parser.add_argument(
        '--no-move-duplicates', action='store_true',
        help='Don\'t move duplicate files to OneDrive'
    )
    local_parser.add_argument(
        '--duplicate-target', type=str, default=None,
        help='Directory to move duplicates to'
    )

    # ==================== ARXIV subcommand ====================
    arxiv_parser = subparsers.add_parser(
        'arxiv',
        help='Recommend from recent arXiv preprints',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python recommend.py arxiv                      # Default: 10 papers, 7 days
  python recommend.py arxiv -k 20 --days 14      # Top 20 from last 2 weeks
  python recommend.py arxiv -c cond-mat          # Only condensed matter
  python recommend.py arxiv -c cond-mat quant-ph # Multiple categories
  python recommend.py arxiv --no-download        # Preview only

Default categories: cs.LG, stat.ML, cond-mat, physics.comp-ph, physics.chem-ph, quant-ph

More categories:
  cond-mat.supr-con   Superconductivity
  cond-mat.str-el     Strongly Correlated Electrons
  cond-mat.mtrl-sci   Materials Science
  hep-lat             Lattice QCD
  cs.AI               Artificial Intelligence
  cs.CL               NLP
        """
    )
    add_common_args(arxiv_parser)
    arxiv_parser.add_argument(
        '--categories', '-c', nargs='+', default=None,
        help='arXiv categories to search'
    )
    arxiv_parser.add_argument(
        '--days', type=int, default=7,
        help='Look back N days (default: 7)'
    )
    arxiv_parser.add_argument(
        '--no-download', action='store_true',
        help='Preview only, don\'t download papers'
    )

    args = parser.parse_args()

    # Default to showing help if no mode given
    if args.mode is None:
        parser.print_help()
        return 0

    try:
        if args.mode == 'local':
            directory = os.path.expanduser(args.directory)
            if not os.path.exists(directory):
                print(f"Error: Directory not found: {directory}")
                return 1

            recommend_local(
                directory=directory,
                top_k=args.top_k,
                verbose=args.verbose,
                recursive=not args.no_recursive,
                tag_recommendations=not args.no_tag,
                surprise_factor=args.surprise,
                max_candidates=args.max_candidates,
                move_duplicates=not args.no_move_duplicates,
                duplicate_target_dir=args.duplicate_target,
            )

        elif args.mode == 'arxiv':
            ref_dir = os.path.expanduser(args.directory)
            if not os.path.exists(ref_dir):
                print(f"Error: Directory not found: {ref_dir}")
                return 1

            # Default max_candidates for arxiv is 100
            max_candidates = args.max_candidates if args.max_candidates else 100

            recommend_arxiv(
                reference_directory=ref_dir,
                output_directory=ref_dir,  # Download to same directory
                categories=args.categories,
                max_candidates=max_candidates,
                days=args.days,
                top_k=args.top_k,
                verbose=args.verbose,
                recursive=not args.no_recursive,
                tag_recommendations=not args.no_tag,
                download=not args.no_download,
                surprise_factor=args.surprise,
            )

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
