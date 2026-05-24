"""
arXiv API client for fetching recent papers.

Uses the arXiv API to search for and download papers.
API docs: https://info.arxiv.org/help/api/index.html
"""

import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import socket
import threading
import time
import os
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
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

    BASE_URL = "https://export.arxiv.org/api/query"
    NAMESPACE = {'atom': 'http://www.w3.org/2005/Atom',
                 'arxiv': 'http://arxiv.org/schemas/atom'}
    MIN_DELAY_SECONDS = 3.0
    DEFAULT_DELAY_SECONDS = 3.1
    DEFAULT_PAGE_SIZE = 200
    MAX_PAGE_SIZE = 2000
    MAX_QUERY_RESULTS = 30000
    DEFAULT_USER_AGENT = "paper-recommender/1.0.0 (academic research tool)"
    _request_lock = threading.Lock()
    _last_request_finished_at = 0.0

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

    def __init__(
        self,
        delay_between_requests: float = DEFAULT_DELAY_SECONDS,
        max_retries: int = 5,
        user_agent: Optional[str] = None,
        contact: Optional[str] = None,
        max_retry_delay: float = 120.0,
    ):
        """
        Initialize arXiv client.

        Args:
            delay_between_requests: Seconds to wait after each arXiv request.
                arXiv asks clients to make no more than one request every
                three seconds, so values below 3.0 are rounded up.
            max_retries: Maximum number of retries on 429, 5xx, and timeout errors
            user_agent: Optional User-Agent override. Can also be set with
                PAPER_RECOMMENDER_USER_AGENT.
            contact: Optional contact email or URL. Can also be set with
                PAPER_RECOMMENDER_CONTACT and is sent in the From header.
            max_retry_delay: Maximum exponential backoff sleep in seconds
        """
        self.delay = max(float(delay_between_requests), self.MIN_DELAY_SECONDS)
        self.max_retries = max_retries
        self.max_retry_delay = max_retry_delay
        self.contact = contact or os.environ.get("PAPER_RECOMMENDER_CONTACT")
        self.user_agent = (
            user_agent
            or os.environ.get("PAPER_RECOMMENDER_USER_AGENT")
            or self.DEFAULT_USER_AGENT
        )

    def _wait_for_rate_limit(self):
        """Respect arXiv rate limiting across all clients in this process."""
        elapsed = time.monotonic() - self.__class__._last_request_finished_at
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _headers(self) -> Dict[str, str]:
        """Build headers for arXiv requests."""
        headers = {'User-Agent': self.user_agent}
        if self.contact:
            headers['From'] = self.contact
        return headers

    @staticmethod
    def _retry_after_seconds(error: urllib.error.HTTPError) -> Optional[float]:
        """Parse a numeric Retry-After header when arXiv sends one."""
        retry_after = error.headers.get('Retry-After') if error.headers else None
        if not retry_after:
            return None
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            return None

    def _retry_delay(self, attempt: int, error: Optional[urllib.error.HTTPError] = None) -> float:
        """Compute conservative retry backoff."""
        delay = self.delay * (2 ** attempt)
        if error is not None:
            retry_after = self._retry_after_seconds(error)
            if retry_after is not None:
                delay = max(delay, retry_after)
        return min(delay, self.max_retry_delay)

    def _request_bytes(self, url: str, timeout: int = 60) -> bytes:
        """Fetch bytes with one in-flight arXiv request per process."""
        req = urllib.request.Request(url, headers=self._headers())
        with self.__class__._request_lock:
            self._wait_for_rate_limit()
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return response.read()
            finally:
                self.__class__._last_request_finished_at = time.monotonic()

    def _fetch_bytes(self, url: str, timeout: int = 60) -> bytes:
        """Fetch bytes with retry on 429, 5xx, and network timeouts."""
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                return self._request_bytes(url, timeout=timeout)
            except urllib.error.HTTPError as e:
                last_error = e
                retryable = e.code == 429 or 500 <= e.code < 600
                if retryable and attempt < self.max_retries - 1:
                    wait_time = self._retry_delay(attempt, e)
                    print(f"  HTTP {e.code}, retrying in {wait_time:.0f}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    raise
            except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self._retry_delay(attempt)
                    print(f"  Network error ({type(e).__name__}: {e}), retrying in {wait_time:.0f}s... (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    raise

        raise RuntimeError(f"Exhausted {self.max_retries} retries: {last_error}")

    def _fetch_url(self, url: str, timeout: int = 60) -> str:
        """Fetch a URL as UTF-8 text."""
        return self._fetch_bytes(url, timeout=timeout).decode('utf-8', errors='replace')

    @staticmethod
    def _business_days_cutoff(days_back: int) -> datetime:
        """Compute cutoff date counting only business days (Mon-Fri).

        arXiv doesn't publish on weekends, so --days 1 on Monday
        should look back to Friday.
        """
        cutoff = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        remaining = days_back
        while remaining > 0:
            cutoff -= timedelta(days=1)
            if cutoff.weekday() < 5:  # Mon=0 .. Fri=4
                remaining -= 1
        return cutoff

    @staticmethod
    def _format_arxiv_date(dt: datetime) -> str:
        """Format datetime for arXiv submittedDate range queries."""
        return dt.strftime("%Y%m%d%H%M")

    def search(self,
               query: Optional[str] = None,
               categories: Optional[List[str]] = None,
               max_results: int = 100,
               days_back: int = 7,
               sort_by: str = "submittedDate",
               sort_order: str = "descending",
               page_size: int = DEFAULT_PAGE_SIZE,
               verbose: bool = False) -> List[Dict]:
        """
        Search for papers on arXiv, paginating in batches of ``page_size``.

        Args:
            query: Search query string (title, abstract, authors)
            categories: List of arXiv categories to search (e.g., ['cs.AI', 'cs.LG'])
            max_results: Maximum number of papers to return (across all pages)
            days_back: Only include papers from the last N business days
            sort_by: Sort field ('submittedDate', 'relevance', 'lastUpdatedDate')
            sort_order: 'ascending' or 'descending'
            page_size: Per-request batch size. Defaults to small slices; arXiv
                supports up to 2,000 per request.
            verbose: Print pagination progress

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
        if max_results <= 0:
            return []

        if max_results > self.MAX_QUERY_RESULTS:
            if verbose:
                print(f"  Limiting arXiv request to {self.MAX_QUERY_RESULTS:,} results")
            max_results = self.MAX_QUERY_RESULTS

        if days_back is not None and days_back < 0:
            raise ValueError("days_back must be non-negative")

        # Date cutoff is used in the API query to avoid asking arXiv to render
        # huge result sets, and again locally as a final guard.
        cutoff_date = self._business_days_cutoff(days_back) if days_back is not None else None

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

        if cutoff_date is not None:
            now_utc = datetime.now(tz=timezone.utc).replace(tzinfo=None)
            start_date = self._format_arxiv_date(cutoff_date)
            end_date = self._format_arxiv_date(now_utc)
            search_parts.append(f"submittedDate:[{start_date} TO {end_date}]")

        search_query = ' AND '.join(search_parts) if search_parts else 'all:*'

        # Early-termination is only valid when paging from newest to oldest.
        can_short_circuit = (
            cutoff_date is not None
            and sort_by == "submittedDate"
            and sort_order == "descending"
        )

        all_papers: List[Dict] = []
        start = 0
        page_size = max(1, min(page_size, self.MAX_PAGE_SIZE))

        while len(all_papers) < max_results:
            batch_size = min(page_size, max_results - len(all_papers))
            params = {
                'search_query': search_query,
                'start': start,
                'max_results': batch_size,
                'sortBy': sort_by,
                'sortOrder': sort_order,
            }
            url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

            try:
                xml_data = self._fetch_url(url)
            except Exception as e:
                # Keep partial results if any pages already succeeded; otherwise propagate.
                if all_papers:
                    print(f"  Warning: pagination stopped at {len(all_papers)} papers ({e})")
                    break
                raise RuntimeError(f"Failed to fetch from arXiv API: {e}")

            page_papers = self._parse_response(xml_data)
            if verbose:
                print(f"  Page start={start}: {len(page_papers)} papers")

            if not page_papers:
                # Empty page → end of results.
                break

            all_papers.extend(page_papers)

            # Last page: arXiv returned fewer than we asked for.
            if len(page_papers) < batch_size:
                break

            # Date short-circuit: once the oldest paper in this page is past the
            # cutoff, every later page will be older too (sorted descending).
            if can_short_circuit:
                oldest = min(
                    (p['published'] for p in page_papers if p.get('published')),
                    default=None,
                )
                if oldest is not None and oldest < cutoff_date:
                    break

            start += batch_size

        # Apply final date filter (the last fetched page may straddle the cutoff).
        if cutoff_date is not None:
            all_papers = [p for p in all_papers if p.get('published') and p['published'] >= cutoff_date]

        return all_papers

    def fetch_by_ids(self, arxiv_ids: List[str], verbose: bool = False) -> List[Dict]:
        """
        Fetch papers by their arXiv IDs.

        Args:
            arxiv_ids: List of arXiv IDs (e.g., ['2603.05164', '2603.05164v1'])
            verbose: Print progress information

        Returns:
            List of paper dictionaries
        """
        if not arxiv_ids:
            return []

        # Keep id_list requests small and predictable. This also avoids long
        # URLs when author pages contain many papers.
        papers = []
        batch_size = 50
        for i in range(0, len(arxiv_ids), batch_size):
            batch_ids = arxiv_ids[i:i + batch_size]
            papers.extend(self._fetch_id_batch(batch_ids, verbose=verbose))

        return papers

    def _fetch_id_batch(self, arxiv_ids: List[str], verbose: bool = False) -> List[Dict]:
        """Fetch one small batch of arXiv IDs."""
        id_list = ','.join(arxiv_ids)
        params = {
            'id_list': id_list,
            'max_results': len(arxiv_ids),
        }
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

        try:
            xml_data = self._fetch_url(url)
            return self._parse_response(xml_data)
        except Exception as e:
            if verbose:
                print(f"  Failed to fetch by IDs: {e}")
            return []

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

        if verbose:
            print(f"  Downloading: {paper['title'][:50]}...")

        try:
            # Add .pdf extension if not present in URL
            pdf_url = paper['pdf_url']
            if not pdf_url.endswith('.pdf'):
                pdf_url = pdf_url + '.pdf'

            pdf_data = self._fetch_bytes(pdf_url, timeout=60)

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

        if verbose:
            print(f"  Fetching HTML: {paper['title'][:50]}...")

        try:
            html_data = self._fetch_url(html_url, timeout=30)

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

    def get_author_papers(self,
                          author_id: str,
                          max_results: int = 200,
                          verbose: bool = False) -> List[Dict]:
        """
        Get papers by an arXiv author ID.

        Args:
            author_id: arXiv author identifier (e.g., 'wang_l_1' from arxiv.org/a/wang_l_1.html)
            max_results: Maximum number of papers to fetch
            verbose: Print progress information

        Returns:
            List of paper dictionaries
        """
        if verbose:
            print(f"Fetching papers for author: {author_id}")

        # Fetch the author page to get paper IDs
        author_url = f"https://arxiv.org/a/{author_id}.html"

        try:
            html_data = self._fetch_url(author_url)
        except Exception as e:
            if verbose:
                print(f"  Failed to fetch author page: {e}")
            return []

        # Extract arXiv IDs from the page (format: arxiv:XXXX.XXXXX or abs/XXXX.XXXXX)
        arxiv_ids = re.findall(r'(?:arxiv:|/abs/)(\d{4}\.\d{4,5}(?:v\d+)?)', html_data)
        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for aid in arxiv_ids:
            if aid not in seen:
                seen.add(aid)
                unique_ids.append(aid)

        if verbose:
            print(f"  Found {len(unique_ids)} papers on author page")

        if not unique_ids:
            return []

        # Limit to max_results
        unique_ids = unique_ids[:max_results]

        # Fetch paper details via API (batch by ID list)
        papers = []
        batch_size = 50  # arXiv API limit per request

        for i in range(0, len(unique_ids), batch_size):
            batch_ids = unique_ids[i:i + batch_size]
            id_list = ','.join(batch_ids)

            params = {
                'id_list': id_list,
                'max_results': len(batch_ids)
            }
            url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

            try:
                xml_data = self._fetch_url(url)
                batch_papers = self._parse_response(xml_data)
                papers.extend(batch_papers)
                if verbose:
                    print(f"  Fetched {len(batch_papers)} papers (batch {i // batch_size + 1})")
            except Exception as e:
                if verbose:
                    print(f"  Failed to fetch batch: {e}")

        if verbose:
            print(f"  Total: {len(papers)} papers retrieved")

        return papers

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
            sort_order="descending",
            verbose=verbose,
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
    arxiv_id = paper.get('arxiv_id', '')
    embedding_key = f"{arxiv_id}#fulltext" if full_text else arxiv_id

    return {
        'path': embedding_key,
        'text': paper_to_text(paper, full_text),
        'title': paper.get('title', ''),
        'author': ', '.join(paper.get('authors', [])),  # All authors
        'filename': f"{paper.get('arxiv_id', 'unknown').replace('/', '_')}.pdf",
        'arxiv_id': paper.get('arxiv_id', ''),
        'pdf_url': paper.get('pdf_url', ''),
        'abstract': paper.get('abstract', ''),
        'categories': paper.get('categories', []),
        'published': paper.get('published'),
    }
