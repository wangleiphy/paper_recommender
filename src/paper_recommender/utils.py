#!/usr/bin/env python3
"""
Shared utilities for paper recommender.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import xattr

from .pdf_extractor import PDFExtractor


def extract_paper_data(pdf_path: str, max_pages: int = 10, verbose: bool = False) -> Optional[Dict[str, str]]:
    """
    Extract text and metadata from a PDF paper.

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum pages to extract (default: 10)
        verbose: Whether to print verbose output

    Returns:
        Dictionary with paper data (path, text, title, author, filename), or None on failure
    """
    try:
        text = PDFExtractor.extract_text(pdf_path, max_pages=max_pages)
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


def move_files_with_pattern(
    files: List[str],
    target_dir: str,
    pattern: str = r'\([0-9]+\)',
    verbose: bool = False
) -> int:
    """
    Move files matching a pattern to a target directory.

    Args:
        files: List of file paths to check
        target_dir: Directory to move matching files to
        pattern: Regex pattern to match in filenames (default: matches (1), (2), etc.)
        verbose: Whether to print verbose output

    Returns:
        Number of files successfully moved
    """
    # Ensure target directory exists
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    # Compile pattern
    regex = re.compile(pattern)

    # Find matching files
    matching_files = [f for f in files if regex.search(os.path.basename(f))]

    if len(matching_files) == 0:
        return 0

    if verbose:
        print(f"Found {len(matching_files)} files matching pattern to move")

    moved_count = 0
    for file_path in matching_files:
        filename = os.path.basename(file_path)
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

            shutil.move(str(file_path), str(target_file))
            moved_count += 1
            if verbose:
                print(f"  ✓ Moved: {filename}")
        except Exception as e:
            if verbose:
                print(f"  ✗ Failed to move {filename}: {e}")

    return moved_count


def copy_extended_attributes(src: str, dest: str) -> bool:
    """
    Copy macOS extended attributes from source to destination file.

    Args:
        src: Source file path
        dest: Destination file path

    Returns:
        True if successful, False otherwise
    """
    try:
        src_attrs = xattr.xattr(src)
        dest_attrs = xattr.xattr(dest)
        for attr in src_attrs.list():
            dest_attrs.set(attr, src_attrs.get(attr))
        return True
    except Exception:
        return False
