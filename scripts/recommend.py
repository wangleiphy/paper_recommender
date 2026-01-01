#!/usr/bin/env python3
"""
Main script for recommending papers similar to red-tagged ones.
"""

import os
import sys
import argparse
import shutil
import re
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector, PDFExtractor, SimilarityEngine


def extract_paper_data(pdf_path: str, verbose: bool = False) -> Dict[str, str]:
    """
    Extract text and metadata from a paper.
    
    Args:
        pdf_path: Path to PDF file
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary with paper data
    """
    try:
        text = PDFExtractor.extract_text(pdf_path, max_pages=10)
        metadata = PDFExtractor.extract_metadata(pdf_path)
        
        return {
            'path': pdf_path,
            'text': text,
            'title': metadata['title'],
            'author': metadata['author'],
            'filename': metadata['filename']
        }
    except Exception as e:
        if verbose:
            print(f"  Warning: Failed to extract from {os.path.basename(pdf_path)}: {e}")
        return None


def move_duplicate_recommendations(recommendations: List, target_dir: str, verbose: bool = False) -> int:
    """
    Move recommended papers with duplicate indicators ((1), (2), etc.) to target directory.
    
    Args:
        recommendations: List of (paper_dict, score) tuples
        target_dir: Directory to move duplicates to
        verbose: Whether to print verbose output
        
    Returns:
        Number of files successfully moved
    """
    # Ensure target directory exists
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Pattern to match (1), (2), etc. in filenames
    duplicate_pattern = re.compile(r'\([0-9]+\)')
    
    duplicate_files = []
    for paper, score in recommendations:
        filename = paper['filename']
        if duplicate_pattern.search(filename):
            duplicate_files.append(paper['path'])
    
    if len(duplicate_files) == 0:
        return 0
    
    if verbose:
        print(f"Found {len(duplicate_files)} duplicate files to move")
    
    moved_count = 0
    for pdf_path in duplicate_files:
        filename = os.path.basename(pdf_path)
        target_file = target_path / filename
        
        try:
            # If file already exists at target, add a unique suffix
            if target_file.exists():
                file_path_obj = Path(filename)
                stem = file_path_obj.stem
                suffix = file_path_obj.suffix
                counter = 1
                while target_file.exists():
                    new_filename = f"{stem}_moved{counter}{suffix}"
                    target_file = target_path / new_filename
                    counter += 1
            
            shutil.move(str(pdf_path), str(target_file))
            moved_count += 1
            if verbose:
                print(f"  ✓ Moved: {filename}")
        except Exception as e:
            if verbose:
                print(f"  ✗ Failed to move {filename}: {e}")
    
    return moved_count


def recommend_papers(
    directory: str,
    top_k: int = None,
    top_k_percent: float = 0.20,
    verbose: bool = False,
    recursive: bool = True,
    tag_recommendations: bool = True,
    surprise_factor: float = 0.2,
    subsample: int = None,
    move_duplicates: bool = True,
    duplicate_target_dir: str = None
):
    """
    Main function to recommend papers.
    
    Args:
        directory: Directory to scan for papers
        top_k: Number of recommendations to return (if None, uses top_k_percent)
        top_k_percent: Percentage of candidates to recommend (default: 0.20 = 20%)
        verbose: Whether to print verbose output
        recursive: Whether to search subdirectories
        tag_recommendations: Whether to tag recommended papers with Gray tag
        surprise_factor: Fraction of recommendations from "surprise" range (0.0-1.0)
        subsample: If specified, randomly sample this many candidate papers (for faster processing)
        move_duplicates: Whether to move duplicate files ((1), (2), etc.) to target directory
        duplicate_target_dir: Directory to move duplicates to (default: OneDrive 文档 folder)
    """
    print("=" * 70)
    print("Paper Recommender")
    print("=" * 70)
    print()
    
    # Step 1: Find red-tagged PDFs
    print(f"[1/4] Scanning directory: {directory}")
    red_tagged_pdfs = TagDetector.find_red_tagged_pdfs(directory, recursive=recursive)
    all_pdfs = TagDetector.find_all_pdfs(directory, recursive=recursive)
    
    print(f"  Found {len(all_pdfs)} total PDF files")
    print(f"  Found {len(red_tagged_pdfs)} red-tagged PDF files")
    print()
    
    if len(red_tagged_pdfs) == 0:
        print("No red-tagged PDF files found!")
        print("Please tag some papers with a red tag in Finder and try again.")
        return
    
    if len(all_pdfs) == len(red_tagged_pdfs):
        print("All PDFs are red-tagged. No papers to recommend.")
        return
    
    # Show red-tagged papers
    print("Red-tagged papers:")
    for pdf_path in red_tagged_pdfs:
        print(f"  ✓ {os.path.basename(pdf_path)}")
    print()
    
    # Step 2: Extract text from ALL red-tagged papers (no sampling)
    # This ensures recommendations are based on your complete set of favorites
    print(f"[2/4] Extracting text from ALL {len(red_tagged_pdfs)} red-tagged papers...")
    reference_papers = []
    
    for pdf_path in tqdm(red_tagged_pdfs, disable=not verbose):
        paper_data = extract_paper_data(pdf_path, verbose=verbose)
        if paper_data:
            reference_papers.append(paper_data)
    
    print(f"  Successfully extracted text from {len(reference_papers)}/{len(red_tagged_pdfs)} papers")
    print()
    
    if len(reference_papers) == 0:
        print("Could not extract text from any red-tagged papers!")
        return
    
    # Step 3: Extract text from candidate papers
    candidate_pdfs = [pdf for pdf in all_pdfs if pdf not in red_tagged_pdfs]
    
    # Subsample candidates if requested
    if subsample and subsample < len(candidate_pdfs):
        import random
        print(f"[3/4] Randomly sampling {subsample} from {len(candidate_pdfs):,} candidate papers...")
        candidate_pdfs = random.sample(candidate_pdfs, subsample)
        print(f"  Sampled {len(candidate_pdfs)} candidates")
        print()
        print(f"  Extracting text from sampled papers...")
    else:
        print(f"[3/4] Extracting text from {len(candidate_pdfs):,} candidate papers...")
    
    candidate_papers = []
    
    for pdf_path in tqdm(candidate_pdfs, disable=not verbose):
        paper_data = extract_paper_data(pdf_path, verbose=verbose)
        if paper_data:
            candidate_papers.append(paper_data)
    
    print(f"  Successfully extracted text from {len(candidate_papers)}/{len(candidate_pdfs)} papers")
    print()
    
    if len(candidate_papers) == 0:
        print("No candidate papers to compare!")
        return
    
    # Calculate top_k if not specified (use percentage)
    if top_k is None:
        top_k = max(5, int(len(candidate_papers) * top_k_percent))
    
    # Cap at available papers
    top_k = min(top_k, len(candidate_papers))
    
    # Step 4: Compute similarities and recommend
    print(f"[4/4] Computing similarities and generating recommendations...")
    print(f"  Will recommend {top_k} papers (~{100*top_k/len(candidate_papers):.1f}% of {len(candidate_papers)} candidates)")
    if surprise_factor > 0:
        print(f"  Surprise factor: {surprise_factor:.0%} (adds variety to recommendations)")
    print()
    
    engine = SimilarityEngine()
    
    # Get embeddings for reference papers
    reference_embeddings = []
    for paper in tqdm(reference_papers, desc="  Processing reference papers", disable=not verbose):
        embedding = engine.get_embedding(paper['text'], paper['path'])
        reference_embeddings.append(embedding)
    
    # Find similar papers with diversity
    recommendations = engine.find_similar_papers_with_diversity(
        reference_embeddings,
        candidate_papers,
        top_k=top_k,
        surprise_factor=surprise_factor
    )
    
    print()
    print("=" * 70)
    print(f"Top {len(recommendations)} Recommended Papers:")
    print("=" * 70)
    print()
    
    for i, (paper, score) in enumerate(recommendations, 1):
        print(f"{i}. {paper['title']}")
        print(f"   Similarity: {score:.4f}")
        print(f"   File: {paper['filename']}")
        if paper['author']:
            print(f"   Author: {paper['author']}")
        print(f"   Path: {paper['path']}")
        print()
    
    # Tag recommended papers with Gray tag
    if tag_recommendations:
        print()
        print("=" * 70)
        print("Tagging Recommendations")
        print("=" * 70)
        print()
        print("Adding 'Gray' tag to papers...")
        
        tagged_count = 0
        for paper, score in recommendations:
            if TagDetector.add_green_tag(paper['path']):
                tagged_count += 1
                if verbose:
                    print(f"  ✓ Tagged: {paper['filename']}")
        
        print(f"Successfully tagged {tagged_count}/{len(recommendations)} papers")
        print()
        
        # Move duplicate files if enabled
        if move_duplicates:
            if duplicate_target_dir is None:
                duplicate_target_dir = '/Users/lewang/Library/CloudStorage/OneDrive-Personal/文档'
            
            moved_count = move_duplicate_recommendations(recommendations, duplicate_target_dir, verbose=verbose)
            if moved_count > 0:
                print()
                print(f"Moved {moved_count} duplicate files to: {duplicate_target_dir}")
                print()
    
    print("=" * 70)
    print(f"✓ Recommendation complete!")
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Recommend papers similar to red-tagged ones',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Recommend 20%% of all candidates
  %(prog)s --subsample 1000             # Sample 1000 papers, recommend 20%%
  %(prog)s --subsample 500 --percent 30 # Sample 500, recommend 30%%
  %(prog)s --top-k 50                   # Recommend exactly 50 papers
  %(prog)s --surprise 0.3 --verbose     # 30%% surprise factor with details
  %(prog)s --directory ~/Documents      # Scan custom directory
        """
    )
    
    parser.add_argument(
        '--directory', '-d',
        default=os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/'),
        help='Directory to scan for papers (default: iCloud Downloads)'
    )
    
    parser.add_argument(
        '--top-k', '-k',
        type=int,
        default=None,
        help='Number of recommendations to show (if not set, uses --percent)'
    )
    
    parser.add_argument(
        '--percent', '-p',
        type=float,
        default=20.0,
        help='Percentage of candidates to recommend (default: 20.0)'
    )
    
    parser.add_argument(
        '--surprise', '-s',
        type=float,
        default=0.2,
        help='Surprise factor: fraction of diverse recommendations (0.0-1.0, default: 0.2)'
    )
    
    parser.add_argument(
        '--subsample', '-n',
        type=int,
        default=None,
        help='Randomly sample N candidate papers for faster processing (default: use all)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress and information'
    )
    
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not search subdirectories'
    )
    
    parser.add_argument(
        '--no-tag',
        action='store_true',
        help='Do not tag recommended papers with Gray tag'
    )
    
    parser.add_argument(
        '--no-move-duplicates',
        action='store_true',
        help='Do not move duplicate files ((1), (2), etc.) to OneDrive folder'
    )
    
    parser.add_argument(
        '--duplicate-target',
        type=str,
        default=None,
        help='Directory to move duplicate files to (default: OneDrive 文档 folder)'
    )
    
    args = parser.parse_args()
    
    # Expand path
    directory = os.path.expanduser(args.directory)
    
    if not os.path.exists(directory):
        print(f"Error: Directory does not exist: {directory}")
        return 1
    
    try:
        recommend_papers(
            directory=directory,
            top_k=args.top_k,
            top_k_percent=args.percent / 100.0,
            verbose=args.verbose,
            recursive=not args.no_recursive,
            tag_recommendations=not args.no_tag,
            surprise_factor=args.surprise,
            subsample=args.subsample,
            move_duplicates=not args.no_move_duplicates,
            duplicate_target_dir=args.duplicate_target
        )
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

