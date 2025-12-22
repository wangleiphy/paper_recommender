#!/usr/bin/env python3
"""
Module for extracting text from PDF files.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


class PDFExtractor:
    """Extract text content from PDF files."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean extracted text by removing extra whitespace and special characters.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)
        
        # Remove extra spaces around punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        
        return text.strip()
    
    @staticmethod
    def extract_with_pymupdf(pdf_path: str, max_pages: Optional[int] = None) -> Optional[str]:
        """
        Extract text using PyMuPDF (fitz).
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to extract (None for all)
            
        Returns:
            Extracted text or None if extraction fails
        """
        if not PYMUPDF_AVAILABLE:
            return None
        
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            
            num_pages = min(len(doc), max_pages) if max_pages else len(doc)
            
            for page_num in range(num_pages):
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            doc.close()
            return '\n'.join(text_parts)
        except Exception as e:
            print(f"PyMuPDF extraction failed for {pdf_path}: {e}")
            return None
    
    @staticmethod
    def extract_with_pypdf2(pdf_path: str, max_pages: Optional[int] = None) -> Optional[str]:
        """
        Extract text using PyPDF2.
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to extract (None for all)
            
        Returns:
            Extracted text or None if extraction fails
        """
        if not PYPDF2_AVAILABLE:
            return None
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text_parts = []
                
                num_pages = min(len(reader.pages), max_pages) if max_pages else len(reader.pages)
                
                for page_num in range(num_pages):
                    page = reader.pages[page_num]
                    text_parts.append(page.extract_text())
                
                return '\n'.join(text_parts)
        except Exception as e:
            print(f"PyPDF2 extraction failed for {pdf_path}: {e}")
            return None
    
    @staticmethod
    def extract_text(pdf_path: str, max_pages: Optional[int] = 10) -> str:
        """
        Extract text from a PDF file using available libraries.
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to extract (default 10 for efficiency)
            
        Returns:
            Extracted and cleaned text
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Try PyMuPDF first (usually faster and better)
        text = PDFExtractor.extract_with_pymupdf(pdf_path, max_pages)
        
        # Fall back to PyPDF2 if PyMuPDF fails
        if not text:
            text = PDFExtractor.extract_with_pypdf2(pdf_path, max_pages)
        
        if not text:
            raise RuntimeError(f"Could not extract text from {pdf_path}")
        
        return PDFExtractor.clean_text(text)
    
    @staticmethod
    def extract_metadata(pdf_path: str) -> Dict[str, str]:
        """
        Extract metadata from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {
            'filename': os.path.basename(pdf_path),
            'path': pdf_path,
            'title': '',
            'author': '',
            'subject': '',
        }
        
        try:
            if PYMUPDF_AVAILABLE:
                doc = fitz.open(pdf_path)
                meta = doc.metadata
                metadata['title'] = meta.get('title', '')
                metadata['author'] = meta.get('author', '')
                metadata['subject'] = meta.get('subject', '')
                doc.close()
            elif PYPDF2_AVAILABLE:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    if reader.metadata:
                        metadata['title'] = reader.metadata.get('/Title', '')
                        metadata['author'] = reader.metadata.get('/Author', '')
                        metadata['subject'] = reader.metadata.get('/Subject', '')
        except Exception as e:
            print(f"Metadata extraction failed for {pdf_path}: {e}")
        
        # Use filename as title if no title in metadata
        if not metadata['title']:
            metadata['title'] = Path(pdf_path).stem
        
        return metadata


if __name__ == '__main__':
    # Test the PDF extractor
    import sys
    
    if len(sys.argv) > 1:
        test_pdf = sys.argv[1]
    else:
        print("Usage: python pdf_extractor.py <path_to_pdf>")
        sys.exit(1)
    
    print(f"Extracting text from: {test_pdf}")
    print()
    
    try:
        # Extract metadata
        metadata = PDFExtractor.extract_metadata(test_pdf)
        print("Metadata:")
        for key, value in metadata.items():
            if value:
                print(f"  {key}: {value}")
        print()
        
        # Extract text
        text = PDFExtractor.extract_text(test_pdf, max_pages=3)
        print(f"Extracted text (first 500 chars):")
        print(text[:500])
        print(f"\n... (total length: {len(text)} characters)")
    except Exception as e:
        print(f"Error: {e}")

