"""Tests for ArxivClient.search query construction.

Root-cause regression test: arXiv's export API times out (HTTP 503 -> 429
cascade) on a single broad query that ORs many categories together and sorts
by submittedDate. The fix is to query one category at a time and merge the
results client-side. These tests pin that behaviour.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from paper_recommender import ArxivClient


def _make_feed(ids):
    """Build a minimal arXiv Atom feed containing the given ids."""
    entries = "".join(
        f"""
  <entry>
    <id>http://arxiv.org/abs/{i}</id>
    <title>Title {i}</title>
    <summary>Abstract {i}</summary>
    <author><name>Author {i}</name></author>
    <link title="pdf" href="http://arxiv.org/pdf/{i}"/>
    <published>2026-05-26T00:00:00Z</published>
    <category term="cs.LG"/>
  </entry>"""
        for i in ids
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom" '
        'xmlns:arxiv="http://arxiv.org/schemas/atom">'
        f"{entries}\n</feed>"
    )


def _client_with_recorder(feeds_by_cat):
    """Return (client, calls) where calls records every fetched URL.

    feeds_by_cat maps a category substring to the list of ids that the fake
    API should return when that substring appears in the request URL.
    """
    client = ArxivClient()
    calls = []

    def fake_fetch_url(url, timeout=60):
        calls.append(url)
        for cat, ids in feeds_by_cat.items():
            if cat.replace(".", ".") in url:
                return _make_feed(ids)
        return _make_feed([])

    client._fetch_url = fake_fetch_url
    return client, calls


def test_each_category_queried_separately():
    """Multiple categories must produce one request per category, never a
    single OR'd union (which is what overloads the arXiv export endpoint)."""
    client, calls = _client_with_recorder(
        {"cs.LG": ["2601.0001", "2601.0002"], "quant-ph": ["2601.0003"]}
    )

    client.search(categories=["cs.LG", "quant-ph"], days_back=None, max_results=50)

    assert len(calls) == 2, f"expected one request per category, got {len(calls)}"
    # No single request may bundle two categories together with OR.
    for url in calls:
        assert " OR " not in url and "+OR+" not in url and "%20OR%20" not in url, (
            f"request OR'd categories together: {url}"
        )


def test_results_deduped_across_categories():
    """A paper cross-listed in two categories appears once in the output."""
    client, _ = _client_with_recorder(
        {
            "cs.LG": ["2601.0001", "2601.0002"],
            "quant-ph": ["2601.0002", "2601.0003"],  # 0002 overlaps
        }
    )

    papers = client.search(
        categories=["cs.LG", "quant-ph"], days_back=None, max_results=50
    )

    ids = sorted(p["arxiv_id"] for p in papers)
    assert ids == ["2601.0001", "2601.0002", "2601.0003"], ids
