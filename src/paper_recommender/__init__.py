"""
Paper Recommender - Intelligent paper recommendation system based on macOS tags.

This package provides tools to:
- Detect macOS Finder tags on PDF files
- Extract text from PDF documents
- Compute semantic similarity using transformer models
- Recommend papers similar to your favorites
"""

__version__ = "1.0.0"

from .tag_detector import TagDetector
from .pdf_extractor import PDFExtractor
from .similarity_engine import SimilarityEngine
from .utils import extract_paper_data, move_files_with_pattern, copy_extended_attributes
from .arxiv_client import ArxivClient, paper_to_text, paper_to_dict

__all__ = [
    "TagDetector",
    "PDFExtractor",
    "SimilarityEngine",
    "extract_paper_data",
    "move_files_with_pattern",
    "copy_extended_attributes",
    "ArxivClient",
    "paper_to_text",
    "paper_to_dict",
]



