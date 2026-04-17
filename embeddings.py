"""
embeddings.py
Handles embedding generation using sentence-transformers (all-MiniLM-L6-v2).
Includes simple in-memory caching.
"""

import hashlib
from typing import List, Dict
import numpy as np

_model = None
_cache: Dict[str, np.ndarray] = {}


def get_model():
    """Lazy-load the embedding model (cached globally)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Embed a list of texts. Uses per-text caching.
    Returns a 2D numpy array of shape (len(texts), embedding_dim).
    """
    model = get_model()
    results = []
    uncached_texts = []
    uncached_indices = []

    for i, text in enumerate(texts):
        key = hashlib.md5(text.encode()).hexdigest()
        if key in _cache:
            results.append((i, _cache[key]))
        else:
            uncached_texts.append(text)
            uncached_indices.append(i)
            results.append((i, None))  # placeholder

    if uncached_texts:
        embeddings = model.encode(uncached_texts, show_progress_bar=False, batch_size=32)
        for j, idx in enumerate(uncached_indices):
            key = hashlib.md5(texts[idx].encode()).hexdigest()
            _cache[key] = embeddings[j]
            results[idx] = (idx, embeddings[j])

    # Sort by original index and stack
    results.sort(key=lambda x: x[0])
    return np.vstack([r[1] for r in results])


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string. Returns 1D numpy array."""
    return embed_texts([query])[0]