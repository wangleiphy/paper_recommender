#!/bin/sh
# Daily arXiv recommendations (20 papers, downloaded + Gray-tagged into iCloud Downloads).
#
# Safe to run at any time of day, and to skip days: the seen ledger
# (.cache/seen_arxiv.json) makes each run score exactly the papers that
# appeared since the previous run. The old `--days 1` window silently missed
# every paper submitted 18:00-02:00 UTC (~30% of arXiv) for a 10:00 UTC+8 run.
set -eu
cd "$(dirname "$0")"   # .cache/ (embeddings + seen ledger) lives in the repo
export PAPER_RECOMMENDER_CONTACT=wangleiphy@gmail.com
exec python scripts/recommend.py arxiv -k 20 "$@"
