"""
vector_store.py
In-memory FAISS vector store — supports build and incremental merge.
"""

from typing import List, Tuple
import numpy as np
from document_loader import DocumentChunk


class VectorStore:
    def __init__(self):
        self.index  = None
        self.chunks: List[DocumentChunk] = []
        self.dim    = None

    def build(self, chunks: List[DocumentChunk], embeddings: np.ndarray):
        """Build a fresh FAISS index from chunks and embeddings."""
        import faiss
        if len(chunks) == 0:
            raise ValueError("No chunks to index.")
        self.chunks = list(chunks)
        self.dim    = embeddings.shape[1]
        faiss.normalize_L2(embeddings.astype(np.float32))
        self.index  = faiss.IndexFlatIP(self.dim)
        self.index.add(embeddings.astype(np.float32))

    def merge(self, new_chunks: List[DocumentChunk], new_embeddings: np.ndarray):
        """
        Add new chunks + embeddings into the existing index.
        If no index exists yet, behaves like build().
        Skips chunks whose source filename is already indexed (dedup by filename).
        """
        import faiss
        if len(new_chunks) == 0:
            return 0

        # Deduplicate: skip files already in the index
        existing_sources = {c.source for c in self.chunks}
        filtered = [(c, e) for c, e in zip(new_chunks, new_embeddings)
                    if c.source not in existing_sources]
        if not filtered:
            return 0  # all files already indexed

        f_chunks = [c for c, _ in filtered]
        f_embs   = np.vstack([e for _, e in filtered]).astype(np.float32)
        faiss.normalize_L2(f_embs)

        if self.index is None:
            self.dim   = f_embs.shape[1]
            self.index = faiss.IndexFlatIP(self.dim)

        self.index.add(f_embs)
        self.chunks.extend(f_chunks)
        return len(f_chunks)

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Tuple[DocumentChunk, float]]:
        """Return top_k most similar chunks."""
        import faiss
        if self.index is None or not self.chunks:
            return []
        q = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(q)
        k = min(top_k, len(self.chunks))
        scores, indices = self.index.search(q, k)
        return [
            (self.chunks[idx], float(score))
            for score, idx in zip(scores[0], indices[0])
            if idx >= 0
        ]

    def indexed_files(self) -> List[str]:
        """Return sorted list of unique filenames currently in the index."""
        return sorted({c.source for c in self.chunks})

    def is_ready(self) -> bool:
        return self.index is not None and len(self.chunks) > 0

    def chunk_count(self) -> int:
        return len(self.chunks)