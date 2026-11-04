#!/usr/bin/env python3
"""
Paper Recommender - Find papers similar to your favorites.

Two modes:
  local  - Recommend from your local PDF collection
  arxiv  - Recommend from recent arXiv preprints

Usage:
  python recommend.py local [options]
  python recommend.py arxiv [options]
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from paper_recommender import TagDetector, SimilarityEngine, ArxivClient, paper_to_dict, paper_to_text
from paper_recommender.utils import extract_paper_data, move_files_with_pattern
from paper_recommender.seen_ledger import SeenLedger, base_arxiv_id, arxiv_ids_in_directory, _ARXIV_FILENAME


# Default paths
DEFAULT_DIRECTORY = os.path.expanduser('~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/')
DEFAULT_DUPLICATE_TARGET = '/Users/lewang/Library/CloudStorage/OneDrive-Personal/文档'

# Default arXiv author ID for reference papers
DEFAULT_AUTHOR_ID = 'wang_l_1'

# Default arXiv categories - Physics + ML/AI
# Categories are queried in order; keep high-volume ML categories last so
# rate-limit failures partway through don't leave an ML-only candidate pool.
DEFAULT_ARXIV_CATEGORIES = [
    'cond-mat',                   # All Condensed Matter
    'physics.comp-ph',            # Computational Physics
    'physics.chem-ph',            # Chemical Physics
    'quant-ph',                   # Quantum Physics
    'cs.LG', 'stat.ML',           # Machine Learning
]
DEFAULT_FULL_TEXT_LIMIT = 50


def get_reference_papers(directory: str, recursive: bool, verbose: bool) -> tuple:
    """Find and extract text from red-tagged reference papers."""
    print(f"Scanning for red-tagged papers: {directory}")
    red_tagged_pdfs = TagDetector.find_red_tagged_pdfs(directory, recursive=recursive)
    print(f"  Found {len(red_tagged_pdfs)} red-tagged PDF files")
    print()

    if len(red_tagged_pdfs) == 0:
        print("No red-tagged PDF files found!")
        print("Please tag some papers with a red tag in Finder and try again.")
        return [], []

    # Show red-tagged papers
    print("Reference papers:")
    for pdf_path in red_tagged_pdfs:
        print(f"  ✓ {os.path.basename(pdf_path)}")
    print()

    # Extract text
    print(f"Extracting text from {len(red_tagged_pdfs)} reference papers...")
    reference_papers = []
    for pdf_path in tqdm(red_tagged_pdfs, disable=not verbose):
        paper_data = extract_paper_data(pdf_path, verbose=verbose)
        if paper_data:
            reference_papers.append(paper_data)

    print(f"  Successfully extracted text from {len(reference_papers)}/{len(red_tagged_pdfs)} papers")
    print()

    return red_tagged_pdfs, reference_papers


def get_tagged_reference_embeddings_arxiv(directory: str, recursive: bool, engine: SimilarityEngine,
                                          client: ArxivClient, verbose: bool) -> tuple:
    """Embed red-tagged papers the same way arXiv candidates are embedded.

    Red PDFs named by arXiv id are represented by their arXiv title+abstract
    (cached under ``ref::<id>``), matching the candidate representation. The
    model only reads the first 384 tokens, which for a PDF is mostly author
    names, affiliations and e-mails. Other PDFs fall back to extracted text.

    Returns (embeddings, base arXiv ids of red papers).
    """
    print(f"Scanning for red-tagged papers: {directory}")
    red_pdfs = TagDetector.find_red_tagged_pdfs(directory, recursive=recursive)
    print(f"  Found {len(red_pdfs)} red-tagged PDF files")
    if not red_pdfs:
        print("  No red-tagged PDF files found (tag favourites red in Finder)")
        return [], set()

    by_id, other = {}, []
    for path in red_pdfs:
        m = _ARXIV_FILENAME.match(os.path.basename(path))
        if m:
            by_id.setdefault(m.group(1), path)
        else:
            other.append(path)

    papers = [{'path': f"ref::{aid}", 'text': ''} for aid in by_id if engine.has_cached(f"ref::{aid}")]
    need = [aid for aid in by_id if not engine.has_cached(f"ref::{aid}")]
    if need:
        print(f"  Fetching arXiv abstracts for {len(need)} new red-tagged papers...")
        got = set()
        for p in client.fetch_by_ids(need, verbose=verbose):
            aid = base_arxiv_id(p.get('arxiv_id', ''))
            if aid in by_id and aid not in got:
                papers.append({'path': f"ref::{aid}", 'text': paper_to_text(p)})
                got.add(aid)
        missing = [aid for aid in need if aid not in got]
        if missing:
            print(f"  {len(missing)} abstracts unavailable; using PDF text for those")
            other.extend(by_id[aid] for aid in missing)

    for path in other:
        if engine.has_cached(path):
            papers.append({'path': path, 'text': ''})
        else:
            data = extract_paper_data(path, verbose=verbose)
            if data:
                papers.append({'path': path, 'text': data['text']})

    n_abs = sum(p['path'].startswith('ref::') for p in papers)
    print(f"  Using {len(papers)} red-tagged references ({n_abs} via arXiv abstract)")
    print()
    return engine.get_embeddings_batch(papers), set(by_id)


def get_author_reference_papers(author_id: str, verbose: bool) -> List[Dict]:
    """Fetch papers from an arXiv author page to use as additional references."""
    print(f"Fetching arXiv preprints for author: {author_id}")

    client = ArxivClient()
    author_papers = client.get_author_papers(author_id, verbose=verbose)

    if not author_papers:
        print("  No papers found for this author")
        return []

    # Convert to reference paper format (using title + abstract as text)
    reference_papers = []
    for paper in author_papers:
        paper_dict = paper_to_dict(paper)
        reference_papers.append(paper_dict)

    print(f"  Found {len(reference_papers)} arXiv preprints")
    print()

    return reference_papers


def get_reference_embeddings(reference_papers: List[Dict], engine: SimilarityEngine, verbose: bool) -> List:
    """Get embeddings for reference papers."""
    reference_embeddings = []
    for paper in tqdm(reference_papers, desc="  Encoding references", disable=not verbose):
        embedding = engine.get_embedding(paper['text'], paper['path'])
        reference_embeddings.append(embedding)
    return reference_embeddings


def print_recommendations(recommendations: List, mode: str = "local"):
    """Print recommendation results."""
    print()
    print("=" * 70)
    title = "Recommended Papers" if mode == "local" else "Recommended arXiv Papers"
    print(f"Top {len(recommendations)} {title}:")
    print("=" * 70)
    print()

    for i, (paper, score) in enumerate(recommendations, 1):
        print(f"{i}. {paper['title']}")
        print(f"   Score: {score:.4f}")

        if mode == "arxiv":
            print(f"   arXiv ID: {paper.get('arxiv_id', 'N/A')}")
            print(f"   Authors: {paper.get('author', 'N/A')}")
            if paper.get('categories'):
                print(f"   Categories: {', '.join(paper['categories'][:3])}")
            if paper.get('published'):
                print(f"   Published: {paper['published'].strftime('%Y-%m-%d')}")
        else:
            print(f"   File: {paper['filename']}")
            if paper['author']:
                print(f"   Author: {paper['author']}")
        print()


def recommend_local(
    directory: str,
    top_k: int = 10,
    verbose: bool = False,
    recursive: bool = True,
    tag_recommendations: bool = True,
    surprise_factor: float = 0.2,
    max_candidates: Optional[int] = None,
    move_duplicates: bool = True,
    duplicate_target_dir: Optional[str] = None,
    refs: str = 'both',
    model_name: str = 'all-mpnet-base-v2',
    scorer: str = 'centroid',
):
    """Recommend papers from local collection."""
    print("=" * 70)
    print("Paper Recommender - Local Mode")
    print("=" * 70)
    print()

    # Step 1: Gather reference papers based on refs mode
    print("[1/4] Finding reference papers...")
    reference_papers = []
    red_tagged_pdfs = []

    if refs in ('tagged', 'both'):
        red_tagged_pdfs, tagged_papers = get_reference_papers(directory, recursive, verbose)
        reference_papers.extend(tagged_papers)

    if refs in ('author', 'both'):
        author_papers = get_author_reference_papers(DEFAULT_AUTHOR_ID, verbose)
        if author_papers:
            reference_papers.extend(author_papers)

    if not reference_papers:
        print("No reference papers found!")
        return

    print(f"  Total reference papers: {len(reference_papers)}")
    print()

    all_pdfs = TagDetector.find_all_pdfs(directory, recursive=recursive)
    print(f"  Found {len(all_pdfs)} total PDF files")
    print()

    if len(all_pdfs) == len(red_tagged_pdfs):
        print("All PDFs are red-tagged. No papers to recommend.")
        return

    # Step 2: Get candidate papers
    candidate_pdfs = [pdf for pdf in all_pdfs if pdf not in red_tagged_pdfs]

    if max_candidates and max_candidates < len(candidate_pdfs):
        import random
        print(f"[2/4] Sampling {max_candidates} from {len(candidate_pdfs):,} candidates...")
        candidate_pdfs = random.sample(candidate_pdfs, max_candidates)
    else:
        print(f"[2/4] Processing {len(candidate_pdfs):,} candidate papers...")

    candidate_papers = []
    for pdf_path in tqdm(candidate_pdfs, disable=not verbose):
        paper_data = extract_paper_data(pdf_path, verbose=verbose)
        if paper_data:
            candidate_papers.append(paper_data)

    print(f"  Extracted text from {len(candidate_papers)}/{len(candidate_pdfs)} papers")
    print()

    if not candidate_papers:
        print("No candidate papers to compare!")
        return

    # Cap top_k at available papers
    top_k = min(top_k, len(candidate_papers))

    # Step 3: Compute similarities
    print(f"[3/4] Computing similarities...")
    print(f"  Will recommend {top_k} papers from {len(candidate_papers)} candidates")
    print()

    engine = SimilarityEngine(model_name=model_name)
    reference_embeddings = get_reference_embeddings(reference_papers, engine, verbose)

    recommendations = engine.find_similar_papers_with_diversity(
        reference_embeddings,
        candidate_papers,
        top_k=top_k,
        surprise_factor=surprise_factor,
        method=scorer,
    )

    print_recommendations(recommendations, mode="local")

    # Step 4: Tag recommendations
    if tag_recommendations:
        print("[4/4] Tagging recommendations...")
        tagged_count = 0
        for paper, score in recommendations:
            if TagDetector.add_green_tag(paper['path']):
                Path(paper['path']).touch()
                tagged_count += 1
                if verbose:
                    print(f"  ✓ Tagged: {paper['filename']}")

        print(f"  Tagged {tagged_count}/{len(recommendations)} papers with Gray")

        # Move duplicates
        if move_duplicates:
            target = duplicate_target_dir or DEFAULT_DUPLICATE_TARGET
            file_paths = [paper['path'] for paper, _ in recommendations]
            moved = move_files_with_pattern(file_paths, target, verbose=verbose)
            if moved > 0:
                print(f"  Moved {moved} duplicate files to: {target}")

    print()
    print("=" * 70)
    print("✓ Done!")
    print("=" * 70)


def recommend_arxiv(
    reference_directory: str,
    output_directory: str,
    categories: Optional[List[str]] = None,
    max_candidates: Optional[int] = None,
    days: int = 3,
    top_k: int = 10,
    verbose: bool = False,
    recursive: bool = True,
    tag_recommendations: bool = True,
    download: bool = True,
    surprise_factor: float = 0.2,
    use_full_text: bool = False,
    max_full_text_fetches: int = DEFAULT_FULL_TEXT_LIMIT,
    refs: str = 'both',
    model_name: str = 'all-mpnet-base-v2',
    scorer: str = 'logreg',
    include_seen: bool = False,
    ledger_path: str = os.path.join('.cache', 'seen_arxiv.json'),
):
    """Recommend papers from arXiv.

    Each run scores only papers not considered by an earlier run (seen
    ledger) and not already present in the output directory, so runs can
    happen at any time of day and missed days are caught up automatically.
    """
    if categories is None:
        categories = DEFAULT_ARXIV_CATEGORIES

    print("=" * 70)
    print("Paper Recommender - arXiv Mode")
    print("=" * 70)
    print()

    client = ArxivClient()
    engine = SimilarityEngine(model_name=model_name)

    # Step 1: Gather reference embeddings based on refs mode
    print("[1/5] Finding reference papers...")
    reference_embeddings = []
    red_ids = set()

    if refs in ('tagged', 'both'):
        tagged_embs, red_ids = get_tagged_reference_embeddings_arxiv(
            reference_directory, recursive, engine, client, verbose)
        reference_embeddings.extend(tagged_embs)

    if refs in ('author', 'both'):
        author_papers = get_author_reference_papers(DEFAULT_AUTHOR_ID, verbose)
        if author_papers:
            reference_embeddings.extend(engine.get_embeddings_batch(author_papers))
            red_ids |= {base_arxiv_id(p['arxiv_id']) for p in author_papers}

    if not reference_embeddings:
        print("No reference papers found!")
        return

    print(f"  Total reference papers: {len(reference_embeddings)}")
    print()

    # Step 2: Fetch from arXiv
    ledger = SeenLedger(ledger_path)
    lookback = ledger.lookback_days(days)
    cap = max_candidates or client.MAX_QUERY_RESULTS
    print(f"[2/5] Fetching from arXiv...")
    print(f"  Categories: {', '.join(categories)}")
    last = ledger.last_run.strftime('%Y-%m-%d %H:%M UTC') if ledger.last_run else 'never'
    print(f"  Last {lookback} business days (previous run: {last}), max {cap} papers")
    print()

    arxiv_papers = client.get_recent_papers(
        categories=categories,
        max_results=cap,
        days_back=lookback,
        verbose=verbose
    )

    print(f"  Retrieved {len(arxiv_papers)} papers")
    if len(arxiv_papers) >= cap:
        print(f"  Warning: hit the {cap}-paper cap; the oldest part of the window was dropped")

    # Only score papers we have not considered before.
    on_disk = arxiv_ids_in_directory(output_directory, recursive=recursive)
    n_disk = sum(base_arxiv_id(p['arxiv_id']) in on_disk for p in arxiv_papers)
    n_seen = sum(p['arxiv_id'] in ledger and base_arxiv_id(p['arxiv_id']) not in on_disk
                 for p in arxiv_papers)
    if include_seen:
        arxiv_papers = [p for p in arxiv_papers if base_arxiv_id(p['arxiv_id']) not in on_disk]
    else:
        arxiv_papers = [p for p in arxiv_papers
                        if base_arxiv_id(p['arxiv_id']) not in on_disk and p['arxiv_id'] not in ledger]
    print(f"  Skipped {n_disk} already in {os.path.basename(output_directory.rstrip('/'))}/"
          + ("" if include_seen else f", {n_seen} scored in earlier runs"))
    print(f"  {len(arxiv_papers)} new candidates")
    print()

    if not arxiv_papers:
        print("No new papers since the last run.")
        if download:
            ledger.save()
        return

    # Fetch full text if requested
    if use_full_text:
        full_text_budget = min(max(0, max_full_text_fetches), len(arxiv_papers))
        print(f"[2.5/5] Fetching full text from arXiv HTML...")
        print(f"  Limit: {full_text_budget}/{len(arxiv_papers)} papers")
        if full_text_budget < len(arxiv_papers):
            print("  Remaining candidates will use title + abstract only")

        full_text_by_id = {}
        success_count = 0
        for paper in tqdm(arxiv_papers[:full_text_budget], desc="  Fetching HTML", disable=not verbose):
            full_text = client.fetch_full_text(paper, verbose=verbose)
            if full_text:
                full_text_by_id[paper.get('arxiv_id', '')] = full_text
                success_count += 1
        candidate_papers = [
            paper_to_dict(paper, full_text_by_id.get(paper.get('arxiv_id', '')))
            for paper in arxiv_papers
        ]
        print(f"  Got full text for {success_count}/{full_text_budget} fetched papers")
        print()
    else:
        candidate_papers = [paper_to_dict(p) for p in arxiv_papers]

    # Step 3: Score candidates
    print(f"[3/5] Scoring candidates (scorer: {scorer})...")
    top_k = min(top_k, len(candidate_papers))
    print(f"  Will recommend {top_k} papers")

    background = None
    if scorer == 'logreg':
        # Past candidates from the cache act as random-arXiv negatives. Exclude
        # anything on disk (earlier recommendations are on-topic, which makes
        # them harmful as negatives), references, and today's candidates.
        exclude = on_disk | red_ids | {base_arxiv_id(p['arxiv_id']) for p in arxiv_papers}
        background = engine.sample_cached_arxiv_embeddings(3000, exclude_ids=exclude)
        print(f"  Background negatives: {len(candidate_papers)} candidates + {len(background)} cached past candidates")
    print()

    recommendations = engine.find_similar_papers_with_diversity(
        reference_embeddings,
        candidate_papers,
        top_k=top_k,
        surprise_factor=surprise_factor,
        method=scorer,
        background_embeddings=background,
    )

    print_recommendations(recommendations, mode="arxiv")

    # Step 4: Download
    if download:
        print("[4/5] Downloading papers...")
        print(f"  Output: {output_directory}")
        os.makedirs(output_directory, exist_ok=True)

        downloaded = []
        for paper, score in tqdm(recommendations, desc="  Downloading"):
            arxiv_id = paper.get('arxiv_id', '')
            original = next((p for p in arxiv_papers if p['arxiv_id'] == arxiv_id), None)
            if original:
                pdf_path = client.download_pdf(original, output_directory, verbose=verbose)
                if pdf_path:
                    downloaded.append((pdf_path, paper, score))

        print(f"  Downloaded {len(downloaded)}/{len(recommendations)} papers")
        print()

        # Step 5: Tag
        if tag_recommendations and downloaded:
            print("[5/5] Tagging papers...")
            tagged = 0
            for pdf_path, paper, score in downloaded:
                if TagDetector.add_green_tag(pdf_path):
                    Path(pdf_path).touch()
                    tagged += 1
                    if verbose:
                        print(f"  ✓ Tagged: {os.path.basename(pdf_path)}")
            print(f"  Tagged {tagged}/{len(downloaded)} papers with Gray")

        # Record every scored candidate as seen, except recommendations whose
        # download failed, so the next run retries those.
        failed = ({p.get('arxiv_id') for p, _ in recommendations}
                  - {p.get('arxiv_id') for _, p, _ in downloaded})
        ledger.mark(p['arxiv_id'] for p in arxiv_papers if p['arxiv_id'] not in failed)
        ledger.save()
        print(f"  Seen ledger: {len(ledger)} papers ({ledger.path})")

    print()
    print("=" * 70)
    print("✓ Done!")
    print("=" * 70)


def add_common_args(parser):
    """Add arguments common to both modes."""
    parser.add_argument(
        '--directory', '-d', default=DEFAULT_DIRECTORY,
        help='Directory with papers (default: iCloud Downloads)'
    )
    parser.add_argument(
        '--top-k', '-k', type=int, default=10,
        help='Number of papers to recommend (default: 10)'
    )
    parser.add_argument(
        '--max-candidates', '-n', type=int, default=None,
        help='Max candidate papers to consider (default: 1000 for local, no cap for arxiv)'
    )
    parser.add_argument(
        '--surprise', '-s', type=float, default=0.2,
        help='Diversity factor 0-1, higher=more variety (default: 0.2)'
    )
    parser.add_argument(
        '--model', '-m', type=str, default='all-mpnet-base-v2',
        help='Sentence transformer model (default: all-mpnet-base-v2, alternative: all-MiniLM-L6-v2)'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--no-recursive', action='store_true',
        help='Don\'t search subdirectories'
    )
    parser.add_argument(
        '--no-tag', action='store_true',
        help='Don\'t tag recommendations with Gray'
    )
    parser.add_argument(
        '--refs', type=str, default='both', choices=['author', 'tagged', 'both'],
        help='Reference source: author (arXiv preprints), tagged (red-tagged PDFs), or both (default: both)'
    )


def main():
    """Main entry point with subcommands."""
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(
        description='Recommend papers similar to your red-tagged favorites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  local   Find similar papers in your local PDF collection
  arxiv   Discover new papers from recent arXiv preprints

Examples:
  python recommend.py local                      # Local recommendations
  python recommend.py local -k 20 -n 1000        # Top 20 from 1000 sampled
  python recommend.py arxiv                      # arXiv recommendations
  python recommend.py arxiv -k 20 --days 14      # Top 20 from last 2 weeks
        """
    )

    subparsers = parser.add_subparsers(dest='mode', help='Recommendation mode')

    # ==================== LOCAL subcommand ====================
    local_parser = subparsers.add_parser(
        'local',
        help='Recommend from local PDF collection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python recommend.py local                 # Recommend 10 papers
  python recommend.py local -k 50           # Recommend 50 papers
  python recommend.py local -n 1000         # Sample 1000 candidates first (faster)
  python recommend.py local -k 20 -n 500    # Top 20 from 500 sampled candidates
        """
    )
    add_common_args(local_parser)
    local_parser.add_argument(
        '--scorer', choices=SimilarityEngine.SCORERS, default='centroid',
        help='Ranking method (default: centroid)'
    )
    local_parser.add_argument(
        '--no-move-duplicates', action='store_true',
        help='Don\'t move duplicate files to OneDrive'
    )
    local_parser.add_argument(
        '--duplicate-target', type=str, default=None,
        help='Directory to move duplicates to'
    )

    # ==================== ARXIV subcommand ====================
    arxiv_parser = subparsers.add_parser(
        'arxiv',
        help='Recommend from recent arXiv preprints',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python recommend.py arxiv                      # Default: 10 new papers since last run
  python recommend.py arxiv -k 20 --days 14      # Top 20 from last 2 weeks
  python recommend.py arxiv -c cond-mat          # Only condensed matter
  python recommend.py arxiv -c cond-mat quant-ph # Multiple categories
  python recommend.py arxiv --no-download        # Preview only

Default categories: cond-mat, physics.comp-ph, physics.chem-ph, quant-ph, cs.LG, stat.ML

More categories:
  cond-mat.supr-con   Superconductivity
  cond-mat.str-el     Strongly Correlated Electrons
  cond-mat.mtrl-sci   Materials Science
  hep-lat             Lattice QCD
  cs.AI               Artificial Intelligence
  cs.CL               NLP
        """
    )
    add_common_args(arxiv_parser)
    arxiv_parser.add_argument(
        '--categories', '-c', nargs='+', default=None,
        help='arXiv categories to search'
    )
    arxiv_parser.add_argument(
        '--days', type=int, default=3,
        help='Minimum lookback in business days (default: 3). Extended automatically '
             'to reach back past the previous run; already-seen papers are skipped.'
    )
    arxiv_parser.add_argument(
        '--scorer', choices=SimilarityEngine.SCORERS, default='logreg',
        help='Ranking method (default: logreg; centroid is the pre-Nov-2026 behaviour)'
    )
    arxiv_parser.add_argument(
        '--include-seen', action='store_true',
        help='Also rescore papers considered by earlier runs (papers already on disk are still skipped)'
    )
    arxiv_parser.add_argument(
        '--no-download', action='store_true',
        help='Preview only, don\'t download papers'
    )
    arxiv_parser.add_argument(
        '--full-text', action='store_true',
        help='Use full text from arXiv HTML (slower but more accurate)'
    )
    arxiv_parser.add_argument(
        '--full-text-limit', type=int, default=DEFAULT_FULL_TEXT_LIMIT,
        help=f'Max arXiv HTML pages to fetch with --full-text (default: {DEFAULT_FULL_TEXT_LIMIT})'
    )

    args = parser.parse_args()

    # Default to showing help if no mode given
    if args.mode is None:
        parser.print_help()
        return 0

    try:
        if args.mode == 'local':
            directory = os.path.expanduser(args.directory)
            if not os.path.exists(directory):
                print(f"Error: Directory not found: {directory}")
                return 1

            recommend_local(
                directory=directory,
                top_k=args.top_k,
                verbose=args.verbose,
                recursive=not args.no_recursive,
                tag_recommendations=not args.no_tag,
                surprise_factor=args.surprise,
                max_candidates=args.max_candidates if args.max_candidates else 1000,
                move_duplicates=not args.no_move_duplicates,
                duplicate_target_dir=args.duplicate_target,
                refs=args.refs,
                model_name=args.model,
                scorer=args.scorer,
            )

        elif args.mode == 'arxiv':
            ref_dir = os.path.expanduser(args.directory)
            if not os.path.exists(ref_dir):
                print(f"Error: Directory not found: {ref_dir}")
                return 1

            # No cap by default: the seen ledger keeps each run's pool to new papers only
            max_candidates = args.max_candidates

            recommend_arxiv(
                reference_directory=ref_dir,
                output_directory=ref_dir,  # Download to same directory
                categories=args.categories,
                max_candidates=max_candidates,
                days=args.days,
                top_k=args.top_k,
                verbose=args.verbose,
                recursive=not args.no_recursive,
                tag_recommendations=not args.no_tag,
                download=not args.no_download,
                surprise_factor=args.surprise,
                use_full_text=args.full_text,
                max_full_text_fetches=args.full_text_limit,
                refs=args.refs,
                model_name=args.model,
                scorer=args.scorer,
                include_seen=args.include_seen,
            )

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
