"""
vector_store.py
In-memory FAISS vector store for storing and retrieving document chunks.
"""

from typing import List, Tuple
import numpy as np
from document_loader import DocumentChunk


class VectorStore:
    def __init__(self):
        self.index = None
        self.chunks: List[DocumentChunk] = []
        self.dim = None

    def build(self, chunks: List[DocumentChunk], embeddings: np.ndarray):
        """Build FAISS index from chunks and their embeddings."""
        import faiss

        if len(chunks) == 0:
            raise ValueError("No chunks to index.")

        self.chunks = chunks
        self.dim = embeddings.shape[1]

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)

        self.index = faiss.IndexFlatIP(self.dim)  # Inner product on normalized = cosine
        self.index.add(embeddings.astype(np.float32))

    def search(self, query_embedding: np.ndarray, top_k: int = 4) -> List[Tuple[DocumentChunk, float]]:
        """Search for top_k most similar chunks."""
        import faiss

        if self.index is None or len(self.chunks) == 0:
            return []

        q = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(q)

        k = min(top_k, len(self.chunks))
        scores, indices = self.index.search(q, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append((self.chunks[idx], float(score)))

        return results

    def is_ready(self) -> bool:
        return self.index is not None and len(self.chunks) > 0

    def chunk_count(self) -> int:
        return len(self.chunks)
