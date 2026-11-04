"""
Ledger of arXiv papers already considered by previous runs.

Why this exists: a rolling ``--days N`` window anchored at "now" leaves gaps.
arXiv announces papers in daily batches, so a window that starts exactly N
business days before the run never contains papers that were submitted just
before the previous run's window start but announced after that run. For a
10:00 (UTC+8) daily run with ``--days 1`` that gap was every paper submitted
18:00-02:00 UTC, about 30% of arXiv. A ledger lets each run fetch a generous
overlapping window and score only the papers it has not seen before, so
coverage no longer depends on when, or how regularly, the job runs.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional, Set

_ARXIV_FILENAME = re.compile(r'^(\d{4}\.\d{4,5})(?:v\d+)?')


def base_arxiv_id(arxiv_id: str) -> str:
    """Strip the version suffix: '2611.01234v2' -> '2611.01234'."""
    return re.sub(r'v\d+$', '', arxiv_id.strip())


def arxiv_ids_in_directory(directory: str, recursive: bool = True) -> Set[str]:
    """Base arXiv ids of PDFs whose filenames start with an arXiv id."""
    found: Set[str] = set()
    if recursive:
        walker = os.walk(directory)
    else:
        walker = [(directory, [], os.listdir(directory))]
    for _, _, files in walker:
        for name in files:
            if name.lower().endswith('.pdf'):
                m = _ARXIV_FILENAME.match(name)
                if m:
                    found.add(m.group(1))
    return found


class SeenLedger:
    """JSON-backed set of base arXiv ids with first-seen timestamps."""

    def __init__(self, path: str = os.path.join('.cache', 'seen_arxiv.json'),
                 retention_days: int = 120):
        self.path = path
        self.retention_days = retention_days
        self.seen: Dict[str, str] = {}
        self.last_run: Optional[datetime] = None
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                self.seen = dict(data.get('seen', {}))
                if data.get('last_run'):
                    self.last_run = datetime.fromisoformat(data['last_run'])
            except (OSError, ValueError) as e:
                print(f"Warning: could not read seen ledger {path}: {e}")

    def __contains__(self, arxiv_id: str) -> bool:
        return base_arxiv_id(arxiv_id) in self.seen

    def __len__(self) -> int:
        return len(self.seen)

    def mark(self, arxiv_ids: Iterable[str]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        for aid in arxiv_ids:
            self.seen.setdefault(base_arxiv_id(aid), now)

    def lookback_days(self, min_days: int, max_days: int = 14) -> int:
        """Window long enough to reach back past the previous run (+2 days slack)."""
        if self.last_run is None:
            return min_days
        elapsed = datetime.now(timezone.utc) - self.last_run
        return max(min_days, min(max_days, elapsed.days + 2))

    def save(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        self.seen = {
            k: v for k, v in self.seen.items()
            if datetime.fromisoformat(v) >= cutoff
        }
        self.last_run = datetime.now(timezone.utc)
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump({'last_run': self.last_run.isoformat(timespec='seconds'),
                       'seen': self.seen}, f)
        os.replace(tmp, self.path)
