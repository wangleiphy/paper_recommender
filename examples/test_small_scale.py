#!/usr/bin/env python3
"""
Test script to run paper recommendation on a small random sample.
"""

import os
import sys
import random
import shutil
import tempfile
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector
from paper_recommender.utils import copy_extended_attributes


def create_test_subset(source_dir: str, sample_size: int = 100):
    """
    Create a temporary directory with a random sample of PDFs.

    Args:
        source_dir: Source directory to sample from
        sample_size: Number of PDFs to sample

    Returns:
        Path to temporary directory
    """
    print(f"Finding PDFs in {source_dir}...")
    all_pdfs = TagDetector.find_all_pdfs(source_dir, recursive=True)

    print(f"Found {len(all_pdfs)} total PDFs")

    if len(all_pdfs) == 0:
        print("No PDFs found!")
        return None

    # Find red-tagged papers
    red_tagged = [pdf for pdf in all_pdfs if TagDetector.has_red_tag(pdf)]
    print(f"Found {len(red_tagged)} red-tagged PDFs")

    if len(red_tagged) == 0:
        print("\nWARNING: No red-tagged PDFs found!")
        print("Please tag some papers with red in Finder first.")
        return None

    # Sample non-tagged papers
    non_tagged = [pdf for pdf in all_pdfs if not TagDetector.has_red_tag(pdf)]

    if len(non_tagged) == 0:
        print("No non-tagged papers to recommend!")
        return None

    # Determine sample size
    # If we have too many red-tagged papers, sample from them too
    if len(red_tagged) >= sample_size:
        print(f"You have {len(red_tagged)} red-tagged papers, sampling {sample_size // 2} of them")
        red_tagged = random.sample(red_tagged, sample_size // 2)
        actual_sample_size = sample_size - len(red_tagged)
    else:
        actual_sample_size = sample_size - len(red_tagged)

    actual_sample_size = min(actual_sample_size, len(non_tagged))
    sampled_non_tagged = random.sample(non_tagged, actual_sample_size)

    print(f"Sampling {actual_sample_size} non-tagged PDFs")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix='paper_recommender_test_')
    print(f"\nCreating test directory: {temp_dir}")

    # Copy red-tagged papers
    print(f"Copying {len(red_tagged)} red-tagged papers...")
    for pdf in red_tagged:
        dest = os.path.join(temp_dir, os.path.basename(pdf))
        shutil.copy2(pdf, dest)
        # Preserve tags by copying extended attributes
        copy_extended_attributes(pdf, dest)
    
    # Copy sampled non-tagged papers
    print(f"Copying {len(sampled_non_tagged)} non-tagged papers...")
    for pdf in sampled_non_tagged:
        dest = os.path.join(temp_dir, os.path.basename(pdf))
        # Handle duplicate filenames
        counter = 1
        while os.path.exists(dest):
            name = Path(pdf).stem
            dest = os.path.join(temp_dir, f"{name}_{counter}.pdf")
            counter += 1
        shutil.copy2(pdf, dest)
    
    print(f"\nTest directory created with {len(red_tagged) + len(sampled_non_tagged)} PDFs")
    print(f"  - {len(red_tagged)} red-tagged")
    print(f"  - {len(sampled_non_tagged)} non-tagged")
    
    return temp_dir


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test paper recommender on a small sample')
    parser.add_argument(
        '--source', '-s',
        default=os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/'),
        help='Source directory to sample from (default: iCloud Downloads)'
    )
    parser.add_argument(
        '--sample-size', '-n',
        type=int,
        default=100,
        help='Number of papers to sample (default: 100)'
    )
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='Keep temporary directory after test'
    )
    parser.add_argument(
        '--top-k', '-k',
        type=int,
        default=5,
        help='Number of recommendations to show (default: 5)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Paper Recommender - Small Scale Test")
    print("=" * 70)
    print()
    
    # Create test subset
    temp_dir = create_test_subset(args.source, args.sample_size)
    
    if temp_dir is None:
        return 1
    
    try:
        print("\n" + "=" * 70)
        print("Running recommendation on test subset...")
        print("=" * 70)
        print()
        
        # Import and run recommender
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from recommend import recommend_papers
        
        recommend_papers(
            directory=temp_dir,
            top_k=args.top_k,
            verbose=True,
            recursive=False,
            tag_recommendations=False  # Don't tag temp files
        )
        
        print("\n" + "=" * 70)
        print("Test completed successfully!")
        print("=" * 70)
        
    finally:
        # Cleanup
        if not args.keep_temp:
            print(f"\nCleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)
        else:
            print(f"\nTemporary directory kept at: {temp_dir}")
    
    return 0


if __name__ == '__main__':
    exit(main())

