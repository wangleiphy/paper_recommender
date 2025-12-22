#!/usr/bin/env python3
"""
Module for computing similarity between papers.
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer


class SimilarityEngine:
    """Computes semantic similarity between papers."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', cache_dir: str = '.cache'):
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
    
    def get_embedding(self, text: str, file_path: str = None) -> np.ndarray:
        """
        Get embedding for a text, using cache if available.
        
        Args:
            text: Text to embed
            file_path: Optional file path for caching
            
        Returns:
            Embedding vector
        """
        # Check cache
        if file_path and file_path in self.embeddings_cache:
            return self.embeddings_cache[file_path]
        
        # Compute embedding
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        
        # Cache it
        if file_path:
            self.embeddings_cache[file_path] = embedding
            self._save_cache()
        
        return embedding
    
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
        
        # Compute embeddings for candidate papers
        candidate_embeddings = []
        for paper in candidate_papers:
            embedding = self.get_embedding(paper['text'], paper['path'])
            candidate_embeddings.append(embedding)
        
        # Compute average reference embedding
        avg_reference_embedding = np.mean(reference_embeddings, axis=0)
        
        # Compute similarity scores
        scores = []
        for i, candidate_embedding in enumerate(candidate_embeddings):
            similarity = self.compute_similarity(avg_reference_embedding, candidate_embedding)
            scores.append((candidate_papers[i], similarity))
        
        # Sort by similarity score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]
    
    def find_similar_papers_with_diversity(
        self,
        reference_embeddings: List[np.ndarray],
        candidate_papers: List[Dict[str, str]],
        top_k: int = 5,
        surprise_factor: float = 0.2
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
        
        # Compute embeddings for candidate papers
        candidate_embeddings = []
        for paper in candidate_papers:
            embedding = self.get_embedding(paper['text'], paper['path'])
            candidate_embeddings.append(embedding)
        
        # Compute average reference embedding
        avg_reference_embedding = np.mean(reference_embeddings, axis=0)
        
        # Compute similarity scores
        scores = []
        for i, candidate_embedding in enumerate(candidate_embeddings):
            similarity = self.compute_similarity(avg_reference_embedding, candidate_embedding)
            scores.append((candidate_papers[i], similarity))
        
        # Sort by similarity score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)
        
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

