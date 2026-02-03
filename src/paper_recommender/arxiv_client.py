"""
arXiv API client for fetching recent papers.

Uses the arXiv API to search for and download papers.
API docs: https://info.arxiv.org/help/api/index.html
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time
import os
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from html.parser import HTMLParser


class ArxivHTMLParser(HTMLParser):
    """Parser to extract text content from arXiv HTML papers."""

    # Tags to skip entirely (including their content)
    SKIP_TAGS = {'script', 'style', 'nav', 'header', 'footer', 'aside', 'figure',
                 'figcaption', 'table', 'math', 'svg', 'button', 'input', 'form'}

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_depth = 0
        self.in_main_content = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Check for main content area
        if tag == 'article' or (tag == 'div' and 'ltx_page_content' in attrs_dict.get('class', '')):
            self.in_main_content = True

        # Skip certain tags
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1

        # Add paragraph breaks
        if tag in ('p', 'div', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append('\n')

    def handle_data(self, data):
        if self.skip_depth == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self) -> str:
        """Get extracted text, cleaned up."""
        text = ' '.join(self.text_parts)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()


class ArxivClient:
    """Client for fetching papers from arXiv API."""

    BASE_URL = "http://export.arxiv.org/api/query"
    NAMESPACE = {'atom': 'http://www.w3.org/2005/Atom',
                 'arxiv': 'http://arxiv.org/schemas/atom'}

    # Common arXiv categories
    CATEGORIES = {
        'cs': 'Computer Science',
        'cs.AI': 'Artificial Intelligence',
        'cs.CL': 'Computation and Language',
        'cs.CV': 'Computer Vision',
        'cs.LG': 'Machine Learning',
        'cs.NE': 'Neural and Evolutionary Computing',
        'stat.ML': 'Machine Learning (Statistics)',
        'physics': 'Physics',
        'cond-mat': 'Condensed Matter',
        'math': 'Mathematics',
        'q-bio': 'Quantitative Biology',
        'q-fin': 'Quantitative Finance',
        'eess': 'Electrical Engineering and Systems Science',
    }

    def __init__(self, delay_between_requests: float = 3.0):
        """
        Initialize arXiv client.

        Args:
            delay_between_requests: Seconds to wait between API calls (arXiv rate limit)
        """
        self.delay = delay_between_requests
        self._last_request_time = 0

    def _wait_for_rate_limit(self):
        """Respect arXiv rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()

    def search(self,
               query: Optional[str] = None,
               categories: Optional[List[str]] = None,
               max_results: int = 100,
               days_back: int = 7,
               sort_by: str = "submittedDate",
               sort_order: str = "descending") -> List[Dict]:
        """
        Search for papers on arXiv.

        Args:
            query: Search query string (title, abstract, authors)
            categories: List of arXiv categories to search (e.g., ['cs.AI', 'cs.LG'])
            max_results: Maximum number of papers to return
            days_back: Only include papers from the last N days
            sort_by: Sort field ('submittedDate', 'relevance', 'lastUpdatedDate')
            sort_order: 'ascending' or 'descending'

        Returns:
            List of paper dictionaries with keys:
            - arxiv_id: arXiv identifier
            - title: Paper title
            - authors: List of author names
            - abstract: Paper abstract
            - pdf_url: URL to download PDF
            - published: Publication date
            - categories: List of arXiv categories
        """
        # Build search query
        search_parts = []

        if query:
            search_parts.append(f'all:{query}')

        if categories:
            # Add wildcard for broad categories (e.g., cond-mat -> cond-mat*)
            # This fixes arXiv API sorting issues with parent categories
            expanded_cats = []
            for cat in categories:
                if '.' not in cat and not cat.endswith('*'):
                    expanded_cats.append(f'{cat}*')
                else:
                    expanded_cats.append(cat)
            cat_query = ' OR '.join(f'cat:{cat}' for cat in expanded_cats)
            search_parts.append(f'({cat_query})')

        search_query = ' AND '.join(search_parts) if search_parts else 'all:*'

        # Build API URL
        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': sort_order
        }

        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

        # Make request
        self._wait_for_rate_limit()

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_data = response.read().decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Failed to fetch from arXiv API: {e}")

        # Parse XML response
        papers = self._parse_response(xml_data)

        # Filter by date if specified
        if days_back:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            papers = [p for p in papers if p['published'] >= cutoff_date]

        return papers

    def _parse_response(self, xml_data: str) -> List[Dict]:
        """Parse arXiv API XML response."""
        root = ET.fromstring(xml_data)
        papers = []

        for entry in root.findall('atom:entry', self.NAMESPACE):
            paper = self._parse_entry(entry)
            if paper:
                papers.append(paper)

        return papers

    def _parse_entry(self, entry: ET.Element) -> Optional[Dict]:
        """Parse a single entry from the API response."""
        try:
            # Get arXiv ID from the id URL
            id_elem = entry.find('atom:id', self.NAMESPACE)
            if id_elem is None:
                return None
            arxiv_id = id_elem.text.split('/abs/')[-1]

            # Get title
            title_elem = entry.find('atom:title', self.NAMESPACE)
            title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else ''

            # Get authors
            authors = []
            for author in entry.findall('atom:author', self.NAMESPACE):
                name = author.find('atom:name', self.NAMESPACE)
                if name is not None:
                    authors.append(name.text)

            # Get abstract
            summary_elem = entry.find('atom:summary', self.NAMESPACE)
            abstract = summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None else ''

            # Get PDF URL
            pdf_url = None
            for link in entry.findall('atom:link', self.NAMESPACE):
                if link.get('title') == 'pdf':
                    pdf_url = link.get('href')
                    break

            # Get publication date
            published_elem = entry.find('atom:published', self.NAMESPACE)
            published = None
            if published_elem is not None:
                try:
                    published = datetime.fromisoformat(published_elem.text.replace('Z', '+00:00'))
                    published = published.replace(tzinfo=None)  # Remove timezone for comparison
                except:
                    published = datetime.now()

            # Get categories
            categories = []
            for category in entry.findall('atom:category', self.NAMESPACE):
                term = category.get('term')
                if term:
                    categories.append(term)

            # Also check arxiv:primary_category
            primary_cat = entry.find('arxiv:primary_category', self.NAMESPACE)
            if primary_cat is not None:
                term = primary_cat.get('term')
                if term and term not in categories:
                    categories.insert(0, term)

            return {
                'arxiv_id': arxiv_id,
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'pdf_url': pdf_url,
                'published': published,
                'categories': categories
            }

        except Exception as e:
            print(f"Warning: Failed to parse arXiv entry: {e}")
            return None

    def download_pdf(self, paper: Dict, output_dir: str, verbose: bool = False) -> Optional[str]:
        """
        Download a paper's PDF.

        Args:
            paper: Paper dictionary from search()
            output_dir: Directory to save the PDF
            verbose: Print progress information

        Returns:
            Path to downloaded PDF, or None if download failed
        """
        if not paper.get('pdf_url'):
            if verbose:
                print(f"  No PDF URL for: {paper['title'][:50]}...")
            return None

        # Create safe filename from arXiv ID
        arxiv_id = paper['arxiv_id'].replace('/', '_')
        filename = f"{arxiv_id}.pdf"
        output_path = os.path.join(output_dir, filename)

        # Skip if already exists
        if os.path.exists(output_path):
            if verbose:
                print(f"  Already exists: {filename}")
            return output_path

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Download PDF
        self._wait_for_rate_limit()

        if verbose:
            print(f"  Downloading: {paper['title'][:50]}...")

        try:
            # Add .pdf extension if not present in URL
            pdf_url = paper['pdf_url']
            if not pdf_url.endswith('.pdf'):
                pdf_url = pdf_url + '.pdf'

            req = urllib.request.Request(
                pdf_url,
                headers={'User-Agent': 'paper_recommender/1.0 (academic research tool)'}
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                pdf_data = response.read()

            with open(output_path, 'wb') as f:
                f.write(pdf_data)

            if verbose:
                size_mb = len(pdf_data) / (1024 * 1024)
                print(f"    Saved: {filename} ({size_mb:.1f} MB)")

            return output_path

        except Exception as e:
            if verbose:
                print(f"    Failed to download: {e}")
            return None

    def fetch_full_text(self, paper: Dict, verbose: bool = False) -> Optional[str]:
        """
        Fetch full text of a paper from arXiv HTML version.

        Args:
            paper: Paper dictionary from search()
            verbose: Print progress information

        Returns:
            Full text content, or None if HTML version unavailable
        """
        arxiv_id = paper.get('arxiv_id', '')
        if not arxiv_id:
            return None

        # arXiv HTML URL format: https://arxiv.org/html/2401.12345
        # Remove version suffix if present (e.g., 2401.12345v1 -> 2401.12345)
        base_id = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
        html_url = f"https://arxiv.org/html/{base_id}"

        self._wait_for_rate_limit()

        if verbose:
            print(f"  Fetching HTML: {paper['title'][:50]}...")

        try:
            req = urllib.request.Request(
                html_url,
                headers={'User-Agent': 'paper_recommender/1.0 (academic research tool)'}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                html_data = response.read().decode('utf-8', errors='ignore')

            # Parse HTML to extract text
            parser = ArxivHTMLParser()
            parser.feed(html_data)
            full_text = parser.get_text()

            if verbose:
                print(f"    Extracted {len(full_text)} characters")

            # Return full text if substantial, otherwise None
            if len(full_text) > 500:
                return full_text
            else:
                if verbose:
                    print(f"    HTML text too short, falling back to abstract")
                return None

        except urllib.error.HTTPError as e:
            if e.code == 404:
                if verbose:
                    print(f"    No HTML version available (404)")
            else:
                if verbose:
                    print(f"    HTTP error: {e.code}")
            return None
        except Exception as e:
            if verbose:
                print(f"    Failed to fetch HTML: {e}")
            return None

    def get_recent_papers(self,
                          categories: List[str],
                          max_results: int = 100,
                          days_back: int = 7,
                          verbose: bool = False) -> List[Dict]:
        """
        Get recent papers from specified categories.

        Convenience method for fetching latest papers.

        Args:
            categories: List of arXiv categories (e.g., ['cs.AI', 'cs.LG'])
            max_results: Maximum number of papers
            days_back: Look back this many days
            verbose: Print progress information

        Returns:
            List of paper dictionaries
        """
        if verbose:
            print(f"Fetching recent papers from arXiv...")
            print(f"  Categories: {', '.join(categories)}")
            print(f"  Looking back {days_back} days")

        papers = self.search(
            categories=categories,
            max_results=max_results,
            days_back=days_back,
            sort_by="submittedDate",
            sort_order="descending"
        )

        if verbose:
            print(f"  Found {len(papers)} papers")

        return papers


def paper_to_text(paper: Dict, full_text: Optional[str] = None) -> str:
    """
    Convert an arXiv paper dict to text suitable for embedding.

    Args:
        paper: Paper dictionary from ArxivClient.search()
        full_text: Optional full text from HTML page (if available)

    Returns:
        Full text if provided, otherwise combined title and abstract
    """
    # Use full text if available
    if full_text:
        return full_text

    # Fall back to title + abstract
    parts = []

    if paper.get('title'):
        parts.append(paper['title'])

    if paper.get('abstract'):
        parts.append(paper['abstract'])

    return ' '.join(parts)


def paper_to_dict(paper: Dict, full_text: Optional[str] = None) -> Dict[str, str]:
    """
    Convert an arXiv paper to the format used by SimilarityEngine.

    Args:
        paper: Paper dictionary from ArxivClient.search()
        full_text: Optional full text from HTML page

    Returns:
        Dictionary compatible with SimilarityEngine methods
    """
    return {
        'path': paper.get('arxiv_id', ''),
        'text': paper_to_text(paper, full_text),
        'title': paper.get('title', ''),
        'author': ', '.join(paper.get('authors', [])[:3]),  # First 3 authors
        'filename': f"{paper.get('arxiv_id', 'unknown').replace('/', '_')}.pdf",
        'arxiv_id': paper.get('arxiv_id', ''),
        'pdf_url': paper.get('pdf_url', ''),
        'abstract': paper.get('abstract', ''),
        'categories': paper.get('categories', []),
        'published': paper.get('published'),
    }
