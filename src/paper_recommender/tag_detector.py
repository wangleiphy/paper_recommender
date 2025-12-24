#!/usr/bin/env python3
"""
Module for detecting macOS Finder tags on files.
"""

import os
import xattr
import plistlib
from pathlib import Path
from typing import List, Set


class TagDetector:
    """Detects macOS Finder tags on files."""
    
    # macOS uses these color codes for Finder tags
    COLOR_CODES = {
        'red': 6,
        'orange': 7,
        'yellow': 5,
        'green': 2,
        'blue': 4,
        'purple': 3,
        'gray': 1,
    }
    
    @staticmethod
    def get_tags(file_path: str) -> List[str]:
        """
        Get all Finder tags for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of tag names
        """
        try:
            # Get extended attributes
            attrs = xattr.xattr(file_path)
            
            # macOS stores tags in com.apple.metadata:_kMDItemUserTags
            if 'com.apple.metadata:_kMDItemUserTags' in attrs:
                tags_data = attrs.get('com.apple.metadata:_kMDItemUserTags')
                tags = plistlib.loads(tags_data)
                return [tag.replace('\n6', '').replace('\n7', '').replace('\n5', '').replace('\n2', '').replace('\n4', '').replace('\n3', '').replace('\n1', '') for tag in tags]
            
            return []
        except (OSError, KeyError):
            return []
    
    @staticmethod
    def set_tag(file_path: str, tag_name: str, color: str = None) -> bool:
        """
        Set a Finder tag on a file.
        
        Args:
            file_path: Path to the file
            tag_name: Name of the tag (e.g., "Gray")
            color: Color of the tag (red, orange, yellow, green, blue, purple, gray)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            attrs = xattr.xattr(file_path)
            
            # Get existing tags
            existing_tags = []
            if 'com.apple.metadata:_kMDItemUserTags' in attrs:
                tags_data = attrs.get('com.apple.metadata:_kMDItemUserTags')
                existing_tags = plistlib.loads(tags_data)
            
            # Create new tag with color code if specified
            if color and color.lower() in TagDetector.COLOR_CODES:
                color_code = TagDetector.COLOR_CODES[color.lower()]
                new_tag = f"{tag_name}\n{color_code}"
            else:
                new_tag = tag_name
            
            # Add tag if not already present
            if new_tag not in existing_tags:
                existing_tags.append(new_tag)
                
                # Save tags
                tags_data = plistlib.dumps(existing_tags)
                attrs.set('com.apple.metadata:_kMDItemUserTags', tags_data)
            
            return True
        except Exception as e:
            print(f"Warning: Could not set tag on {file_path}: {e}")
            return False
    
    @staticmethod
    def add_green_tag(file_path: str, tag_name: str = "Gray") -> bool:
        """
        Add a tag to a file.
        
        Args:
            file_path: Path to the file
            tag_name: Name of the tag (default: "Gray")
            
        Returns:
            True if successful, False otherwise
        """
        return TagDetector.set_tag(file_path, tag_name)
    
    @staticmethod
    def has_red_tag(file_path: str) -> bool:
        """
        Check if a file has a red tag.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file has red tag, False otherwise
        """
        tags = TagDetector.get_tags(file_path)
        
        # Check for red tag (can be just color code or named tag)
        for tag in tags:
            if 'red' in tag.lower() or '\n6' in tag:
                return True
        
        # Alternative: check the Finder info extended attribute
        try:
            attrs = xattr.xattr(file_path)
            if 'com.apple.FinderInfo' in attrs:
                finder_info = attrs.get('com.apple.FinderInfo')
                if len(finder_info) >= 10:
                    # Byte 9 contains the color tag
                    color_code = finder_info[9]
                    if color_code == (TagDetector.COLOR_CODES['red'] * 2):  # Red is stored as 12 (6*2)
                        return True
        except (OSError, KeyError):
            pass
        
        return False
    
    @staticmethod
    def find_red_tagged_pdfs(directory: str, recursive: bool = True) -> List[str]:
        """
        Find all red-tagged PDF files in a directory.
        
        Args:
            directory: Directory to search
            recursive: Whether to search subdirectories
            
        Returns:
            List of paths to red-tagged PDF files
        """
        red_tagged_files = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"Warning: Directory {directory} does not exist")
            return []
        
        # Search for PDF files
        pattern = '**/*.pdf' if recursive else '*.pdf'
        
        for pdf_file in directory_path.glob(pattern):
            if pdf_file.is_file() and TagDetector.has_red_tag(str(pdf_file)):
                red_tagged_files.append(str(pdf_file))
        
        return red_tagged_files
    
    @staticmethod
    def find_all_pdfs(directory: str, recursive: bool = True) -> List[str]:
        """
        Find all PDF files in a directory.
        
        Args:
            directory: Directory to search
            recursive: Whether to search subdirectories
            
        Returns:
            List of paths to all PDF files
        """
        pdf_files = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"Warning: Directory {directory} does not exist")
            return []
        
        # Search for PDF files
        pattern = '**/*.pdf' if recursive else '*.pdf'
        
        for pdf_file in directory_path.glob(pattern):
            if pdf_file.is_file():
                pdf_files.append(str(pdf_file))
        
        return pdf_files


if __name__ == '__main__':
    # Test the tag detector
    import sys
    
    if len(sys.argv) > 1:
        test_dir = sys.argv[1]
    else:
        test_dir = os.path.expanduser('~/Downloads')
    
    print(f"Scanning directory: {test_dir}")
    print()
    
    red_tagged = TagDetector.find_red_tagged_pdfs(test_dir)
    all_pdfs = TagDetector.find_all_pdfs(test_dir)
    
    print(f"Found {len(all_pdfs)} total PDF files")
    print(f"Found {len(red_tagged)} red-tagged PDF files:")
    print()
    
    for file_path in red_tagged:
        print(f"  ✓ {os.path.basename(file_path)}")
        tags = TagDetector.get_tags(file_path)
        if tags:
            print(f"    Tags: {', '.join(tags)}")

