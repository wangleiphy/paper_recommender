#!/usr/bin/env python3
"""
Module for computing similarity between papers.
"""

import os
import pickle
import random
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


def _l2(x: np.ndarray) -> np.ndarray:
    """L2-normalise along the last axis."""
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)


class SimilarityEngine:
    """Computes semantic similarity between papers."""
    
    def __init__(self, model_name: str = 'all-mpnet-base-v2', cache_dir: str = '.cache'):
        """
        Initialize the similarity engine.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            cache_dir: Directory to cache embeddings
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = None
        self.embeddings_cache = {}
        
        # Create cache directory
        Path(cache_dir).mkdir(exist_ok=True)
        self.cache_file = os.path.join(cache_dir, 'embeddings_cache.pkl')
        
        # Load cache if exists
        self._load_cache()
    
    def _load_cache(self):
        """Load embeddings cache from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.embeddings_cache = pickle.load(f)
                print(f"Loaded {len(self.embeddings_cache)} cached embeddings")
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
                self.embeddings_cache = {}
    
    def _save_cache(self):
        """Save embeddings cache to disk."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.embeddings_cache, f)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    def _get_model(self):
        """Lazy load the sentence transformer model."""
        if self.model is None:
            print(f"Loading model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
        return self.model
    
    def _cache_key(self, file_path: str) -> str:
        # Key includes model name to avoid mixing dimensions
        return f"{self.model_name}::{file_path}"

    def has_cached(self, file_path: str) -> bool:
        """Whether an embedding for this key is already cached."""
        return self._cache_key(file_path) in self.embeddings_cache

    def get_embedding(self, text: str, file_path: str = None, save: bool = True) -> np.ndarray:
        """
        Get embedding for a text, using cache if available.

        Args:
            text: Text to embed
            file_path: Optional file path for caching
            save: Write the cache to disk after adding a new entry

        Returns:
            Embedding vector
        """
        cache_key = self._cache_key(file_path) if file_path else None
        if cache_key and cache_key in self.embeddings_cache:
            return self.embeddings_cache[cache_key]

        # Compute embedding
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)

        # Cache it
        if cache_key:
            self.embeddings_cache[cache_key] = embedding
            if save:
                self._save_cache()

        return embedding

    def sample_cached_arxiv_embeddings(self, n: int, exclude_ids=(), seed: int = 0) -> np.ndarray:
        """
        Sample cached title+abstract embeddings of past arXiv candidates.

        These are effectively random papers from the configured categories,
        which makes them good background negatives for the logreg scorer.
        """
        prefix = f"{self.model_name}::"
        exclude = set(exclude_ids)
        pat = re.compile(r'^\d{4}\.\d{4,5}(v\d+)?$')
        pool = []
        for key, emb in self.embeddings_cache.items():
            if not key.startswith(prefix):
                continue
            ident = key[len(prefix):]
            if pat.match(ident) and re.sub(r'v\d+$', '', ident) not in exclude:
                pool.append(emb)
        if not pool:
            return np.zeros((0, 0))
        rng = random.Random(seed)
        if len(pool) > n:
            pool = rng.sample(pool, n)
        return np.vstack(pool)
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0 to 1)
        """
        return cosine_similarity([embedding1], [embedding2])[0][0]

    def get_embeddings_batch(self, papers: List[Dict[str, str]]) -> List[np.ndarray]:
        """
        Get embeddings for multiple papers.

        Args:
            papers: List of paper dicts with 'path' and 'text'

        Returns:
            List of embedding vectors
        """
        # Encode all uncached texts in one batch and write the cache once.
        # (Saving the whole pickle after every new paper made each run
        # rewrite a multi-MB file hundreds of times.)
        missing = [p for p in papers if not self.has_cached(p['path'])]
        if missing:
            model = self._get_model()
            new = model.encode([p['text'] for p in missing], batch_size=32,
                               convert_to_numpy=True, show_progress_bar=False)
            for p, emb in zip(missing, new):
                self.embeddings_cache[self._cache_key(p['path'])] = emb
            self._save_cache()
        return [self.embeddings_cache[self._cache_key(p['path'])] for p in papers]

    SCORERS = ('logreg', 'knn', 'centroid')

    def score_embeddings(
        self,
        reference_embeddings: List[np.ndarray],
        candidate_embeddings: np.ndarray,
        method: str = 'centroid',
        background_embeddings: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Score candidates against the reference set.

        Methods (offline eval, Nov 2026: 77 held-out red-tagged papers ranked
        within a real 3,168-paper arXiv week; recall within the top 1%):
          centroid  cosine to the mean reference embedding (old default; 0.21)
          knn       soft-max over per-reference cosines, tau=0.05 (0.32-0.35)
          logreg    logistic regression, references vs. background papers
                    (the candidates themselves + cached past candidates) (0.42-0.48)
        """
        R = _l2(np.asarray(reference_embeddings, dtype=np.float32))
        C = _l2(np.asarray(candidate_embeddings, dtype=np.float32))
        if method == 'centroid':
            return C @ _l2(R.mean(0))
        if method == 'knn':
            tau = 0.05
            s = (C @ R.T) / tau
            m = s.max(1, keepdims=True)
            return tau * (m[:, 0] + np.log(np.exp(s - m).sum(1)))
        if method == 'logreg':
            from sklearn.linear_model import LogisticRegression
            negs = [C]
            if background_embeddings is not None and len(background_embeddings):
                negs.append(_l2(np.asarray(background_embeddings, dtype=np.float32)))
            N = np.vstack(negs)
            if len(R) < 5:
                print("  Fewer than 5 references; falling back to knn scorer")
                return self.score_embeddings(R, C, method='knn')
            X = np.vstack([R, N])
            y = np.r_[np.ones(len(R)), np.zeros(len(N))]
            clf = LogisticRegression(C=1.0, class_weight='balanced', max_iter=3000)
            clf.fit(X, y)
            return clf.decision_function(C)
        raise ValueError(f"Unknown scorer {method!r}; choose from {self.SCORERS}")

    def _compute_candidate_scores(
        self,
        reference_embeddings: List[np.ndarray],
        candidate_papers: List[Dict[str, str]],
        method: str = 'centroid',
        background_embeddings: Optional[np.ndarray] = None,
    ) -> List[Tuple[Dict[str, str], float]]:
        """
        Compute scores for all candidates against reference embeddings.

        Returns:
            List of (paper_dict, score) tuples, sorted by score descending
        """
        candidate_embeddings = np.vstack(self.get_embeddings_batch(candidate_papers))
        values = self.score_embeddings(reference_embeddings, candidate_embeddings,
                                       method=method, background_embeddings=background_embeddings)
        scores = [(paper, float(v)) for paper, v in zip(candidate_papers, values)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def find_similar_papers(
        self,
        reference_embeddings: List[np.ndarray],
        candidate_papers: List[Dict[str, str]],
        top_k: int = 5
    ) -> List[Tuple[Dict[str, str], float]]:
        """
        Find papers most similar to reference papers.

        This computes the average embedding across ALL reference papers,
        ensuring recommendations reflect your complete set of preferences.

        Args:
            reference_embeddings: List of embeddings for ALL reference papers
            candidate_papers: List of candidate paper dicts with 'path' and 'text'
            top_k: Number of top recommendations to return

        Returns:
            List of (paper_dict, similarity_score) tuples, sorted by score
        """
        if not reference_embeddings or not candidate_papers:
            return []

        scores = self._compute_candidate_scores(reference_embeddings, candidate_papers)
        return scores[:top_k]

    def find_similar_papers_with_diversity(
        self,
        reference_embeddings: List[np.ndarray],
        candidate_papers: List[Dict[str, str]],
        top_k: int = 5,
        surprise_factor: float = 0.2,
        method: str = 'centroid',
        background_embeddings: Optional[np.ndarray] = None,
    ) -> List[Tuple[Dict[str, str], float]]:
        """
        Find papers similar to reference papers with added diversity/surprise.

        This method adds variety to recommendations by:
        - Including top matches (80% by default)
        - Including some "surprise" papers from deeper in the ranking (20% by default)

        Args:
            reference_embeddings: List of embeddings for ALL reference papers
            candidate_papers: List of candidate paper dicts with 'path' and 'text'
            top_k: Number of recommendations to return
            surprise_factor: Fraction of results to include from "surprise" range (0.0-1.0)

        Returns:
            List of (paper_dict, similarity_score) tuples with diversity
        """
        if not reference_embeddings or not candidate_papers:
            return []

        scores = self._compute_candidate_scores(reference_embeddings, candidate_papers,
                                                method=method,
                                                background_embeddings=background_embeddings)

        # Calculate split between top matches and surprise papers
        num_top = max(1, int(top_k * (1 - surprise_factor)))
        num_surprise = top_k - num_top

        # Get top matches
        recommendations = scores[:num_top]

        # Add surprise papers from the next tier
        # Sample from papers ranked between top_k and top_k * 3
        if num_surprise > 0 and len(scores) > top_k:
            surprise_start = top_k
            surprise_end = min(len(scores), top_k * 3)

            if surprise_end > surprise_start:
                import random
                surprise_pool = scores[surprise_start:surprise_end]
                # Sample without replacement
                num_available = min(num_surprise, len(surprise_pool))
                surprise_papers = random.sample(surprise_pool, num_available)
                recommendations.extend(surprise_papers)

        # Shuffle slightly to mix top and surprise papers
        import random
        if surprise_factor > 0:
            # Keep the very top paper, shuffle the rest
            if len(recommendations) > 1:
                top_paper = recommendations[0]
                rest = recommendations[1:]
                random.shuffle(rest)
                recommendations = [top_paper] + rest

        return recommendations[:top_k]
    
    def compute_pairwise_similarities(
        self,
        papers: List[Dict[str, str]]
    ) -> np.ndarray:
        """
        Compute pairwise similarity matrix for a list of papers.
        
        Args:
            papers: List of paper dicts with 'path' and 'text'
            
        Returns:
            Similarity matrix (n x n)
        """
        # Compute embeddings
        embeddings = []
        for paper in papers:
            embedding = self.get_embedding(paper['text'], paper['path'])
            embeddings.append(embedding)
        
        # Compute pairwise similarities
        embeddings_array = np.array(embeddings)
        similarity_matrix = cosine_similarity(embeddings_array)
        
        return similarity_matrix


if __name__ == '__main__':
    # Test the similarity engine
    engine = SimilarityEngine()
    
    # Test texts
    text1 = "Machine learning is a subset of artificial intelligence that focuses on learning from data."
    text2 = "Deep learning uses neural networks with multiple layers to learn hierarchical representations."
    text3 = "Quantum computing uses quantum mechanics to process information in fundamentally different ways."
    
    # Compute embeddings
    emb1 = engine.get_embedding(text1)
    emb2 = engine.get_embedding(text2)
    emb3 = engine.get_embedding(text3)
    
    # Compute similarities
    sim_1_2 = engine.compute_similarity(emb1, emb2)
    sim_1_3 = engine.compute_similarity(emb1, emb3)
    sim_2_3 = engine.compute_similarity(emb2, emb3)
    
    print("Similarity scores:")
    print(f"  ML vs Deep Learning: {sim_1_2:.4f}")
    print(f"  ML vs Quantum: {sim_1_3:.4f}")
    print(f"  Deep Learning vs Quantum: {sim_2_3:.4f}")

