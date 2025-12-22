"""Setup script for paper_recommender package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="paper-recommender",
    version="1.0.0",
    author="Your Name",
    description="Intelligent paper recommendation system based on macOS tags and semantic similarity",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/paper-recommender",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "pypdf2>=3.0.0",
        "PyMuPDF>=1.23.0",
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "sentence-transformers>=2.2.0",
        "xattr>=1.0.0",
        "tqdm>=4.65.0",
    ],
    entry_points={
        "console_scripts": [
            "paper-recommend=scripts.recommend:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="paper recommendation, pdf, machine learning, semantic similarity, tags",
)

