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

__all__ = ["TagDetector", "PDFExtractor", "SimilarityEngine"]

