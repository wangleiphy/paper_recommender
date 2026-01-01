#!/usr/bin/env python3
"""
Script to find and move duplicate recommended papers to OneDrive folder.
"""

import os
import sys
import shutil
import re
from pathlib import Path

# Add src/paper_recommender directory to path
src_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'paper_recommender')
sys.path.insert(0, src_path)

import tag_detector
TagDetector = tag_detector.TagDetector


def find_duplicate_recommendations(source_dir: str, target_dir: str):
    """
    Find Gray-tagged PDFs with duplicate indicators and move them to target directory.
    
    Args:
        source_dir: Directory to search for duplicate files
        target_dir: Directory to move duplicates to
    """
    # Ensure target directory exists
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Find all PDFs
    print(f"Scanning for PDFs in: {source_dir}")
    all_pdfs = TagDetector.find_all_pdfs(source_dir, recursive=True)
    print(f"Found {len(all_pdfs)} total PDF files")
    print()
    
    # Pattern to match (1), (2), etc. in filenames
    duplicate_pattern = re.compile(r'\([0-9]+\)')
    duplicate_files = []
    
    print("Checking for Gray-tagged duplicates...")
    for pdf_path in all_pdfs:
        filename = os.path.basename(pdf_path)
        if duplicate_pattern.search(filename):
            tags = TagDetector.get_tags(pdf_path)
            # Check if 'Gray' tag is present
            gray_tagged = any('gray' in tag.lower() for tag in tags)
            if gray_tagged:
                duplicate_files.append(pdf_path)
    
    print(f"Found {len(duplicate_files)} duplicate files with Gray tag")
    print()
    
    if len(duplicate_files) == 0:
        print("No duplicate files found to move.")
        return
    
    # Move files
    moved_count = 0
    failed_count = 0
    
    print("Moving files to OneDrive folder...")
    for pdf_path in duplicate_files:
        filename = os.path.basename(pdf_path)
        target_file = target_path / filename
        
        try:
            # If file already exists at target, add a unique suffix
            if target_file.exists():
                stem = target_path / Path(filename).stem
                suffix = Path(filename).suffix
                counter = 1
                while target_file.exists():
                    target_file = Path(f"{stem}_moved{counter}{suffix}")
                    counter += 1
            
            shutil.move(str(pdf_path), str(target_file))
            moved_count += 1
            print(f"  ✓ Moved: {filename}")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Failed to move {filename}: {e}")
    
    print()
    print(f"Successfully moved {moved_count}/{len(duplicate_files)} files")
    if failed_count > 0:
        print(f"Failed to move {failed_count} files")
    print(f"Target directory: {target_dir}")


if __name__ == '__main__':
    source_dir = os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/')
    target_dir = '/Users/lewang/Library/CloudStorage/OneDrive-Personal/文档'
    
    find_duplicate_recommendations(source_dir, target_dir)

