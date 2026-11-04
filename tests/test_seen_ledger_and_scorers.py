"""Tests for the seen ledger and the candidate scorers."""

import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from paper_recommender.seen_ledger import SeenLedger, base_arxiv_id, arxiv_ids_in_directory
from paper_recommender.similarity_engine import SimilarityEngine


def test_base_arxiv_id_strips_version():
    assert base_arxiv_id("2611.01234v3") == "2611.01234"
    assert base_arxiv_id("2611.01234") == "2611.01234"


def test_ledger_roundtrip_and_version_insensitive(tmp_path):
    path = str(tmp_path / "seen.json")
    led = SeenLedger(path)
    assert led.last_run is None and "2611.00001v1" not in led
    led.mark(["2611.00001v1", "2611.00002v2"])
    led.save()

    again = SeenLedger(path)
    assert "2611.00001v2" in again          # other version of a seen paper
    assert "2611.00003v1" not in again
    assert again.last_run is not None


def test_lookback_covers_gap_since_last_run(tmp_path):
    led = SeenLedger(str(tmp_path / "seen.json"))
    assert led.lookback_days(3) == 3                       # first run
    led.last_run = datetime.now(timezone.utc) - timedelta(days=6)
    assert led.lookback_days(3) == 8                       # 6 days elapsed + 2 slack
    led.last_run = datetime.now(timezone.utc) - timedelta(days=60)
    assert led.lookback_days(3) == 14                      # capped


def test_ledger_prunes_old_entries(tmp_path):
    path = str(tmp_path / "seen.json")
    led = SeenLedger(path, retention_days=10)
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    led.seen = {"2601.00001": old}
    led.mark(["2611.00001"])
    led.save()
    assert set(SeenLedger(path).seen) == {"2611.00001"}


def test_arxiv_ids_in_directory(tmp_path):
    (tmp_path / "sub").mkdir()
    for name in ["2611.01234v1.pdf", "sub/2610.99999v2(1).pdf", "notes.pdf", "2611.05555v1.txt"]:
        (tmp_path / name).write_text("x")
    assert arxiv_ids_in_directory(str(tmp_path)) == {"2611.01234", "2610.99999"}
    assert arxiv_ids_in_directory(str(tmp_path), recursive=False) == {"2611.01234"}


def _toy(seed=0, d=16):
    """References cluster around two topics; one candidate per topic plus noise."""
    rng = np.random.default_rng(seed)
    a, b = rng.normal(size=d), rng.normal(size=d)
    refs = np.vstack([a + 0.1 * rng.normal(size=(20, d)), b + 0.1 * rng.normal(size=(5, d))])
    noise = rng.normal(size=(200, d))
    cands = np.vstack([a + 0.1 * rng.normal(size=d), b + 0.1 * rng.normal(size=d), noise])
    return refs, cands


def test_scorers_rank_on_topic_candidates_first():
    eng = SimilarityEngine.__new__(SimilarityEngine)       # no model / cache needed
    refs, cands = _toy()
    for method in SimilarityEngine.SCORERS:
        s = eng.score_embeddings(list(refs), cands, method=method)
        top = set(np.argsort(-s)[:5])
        assert 0 in top, method
        if method != 'centroid':
            # minority interest (5 of 25 refs) must not be drowned out by the majority
            assert 1 in top, method


def test_logreg_falls_back_with_few_references():
    eng = SimilarityEngine.__new__(SimilarityEngine)
    refs, cands = _toy()
    s = eng.score_embeddings(list(refs[:3]), cands, method='logreg')
    assert s.shape == (len(cands),)
