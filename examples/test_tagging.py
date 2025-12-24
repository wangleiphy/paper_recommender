#!/usr/bin/env python3
"""
Test script to verify Gray tagging functionality.
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector

def test_tagging():
    """Test the Gray tagging functionality."""
    
    print("=" * 70)
    print("Gray Tagging Test")
    print("=" * 70)
    print()
    
    # Find a test PDF to tag
    test_dir = os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/')
    
    print(f"Finding test PDFs in: {test_dir}")
    all_pdfs = TagDetector.find_all_pdfs(test_dir, recursive=True)
    
    if not all_pdfs:
        print("No PDFs found!")
        return 1
    
    # Get non-tagged PDFs
    non_tagged = [pdf for pdf in all_pdfs if not TagDetector.has_red_tag(pdf)]
    
    if len(non_tagged) < 1:
        print("No non-tagged PDFs found for testing!")
        return 1
    
    # Test on the first non-tagged PDF
    test_pdf = non_tagged[0]
    print(f"Test file: {os.path.basename(test_pdf)}")
    print()
    
    # Show current tags
    print("Current tags:")
    current_tags = TagDetector.get_tags(test_pdf)
    if current_tags:
        for tag in current_tags:
            print(f"  - {tag}")
    else:
        print("  (none)")
    print()
    
    # Add Gray tag
    print("Adding 'Gray' tag...")
    success = TagDetector.add_green_tag(test_pdf)
    
    if success:
        print("✓ Successfully tagged!")
    else:
        print("✗ Failed to tag")
        return 1
    
    print()
    
    # Verify tag was added
    print("Verifying tag...")
    new_tags = TagDetector.get_tags(test_pdf)
    print("Tags after adding Gray tag:")
    for tag in new_tags:
        print(f"  - {tag}")
    
    print()
    print("=" * 70)
    print("Test completed!")
    print("=" * 70)
    print()
    print("Check in Finder to verify the Gray tag appears on:")
    print(f"  {os.path.basename(test_pdf)}")
    print()
    
    return 0


if __name__ == '__main__':
    exit(test_tagging())

