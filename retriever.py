"""
retriever.py
Hybrid retrieval: semantic (FAISS cosine) + keyword (BM25-style TF scoring).
Supports dynamic top-k and returns scored, deduplicated candidates.
"""

import math
import re
from typing import List, Tuple, Dict
import numpy as np

from document_loader import DocumentChunk
from vector_store import VectorStore


# ── Tuneable constants ────────────────────────────────────────────────────────
SEMANTIC_TOP_K   = 10    # candidates pulled from FAISS before re-ranking
KEYWORD_WEIGHT   = 0.35  # blend weight for keyword score  (1-w for semantic)
SEMANTIC_WEIGHT  = 0.65
MIN_SCORE_THRESH = 0.10  # discard chunks below this blended score
MAX_FINAL_K      = 6     # maximum chunks sent to the generator


class HybridRetriever:
    """
    Combines FAISS semantic search with lightweight BM25-style keyword scoring.
    """

    def retrieve(
        self,
        query: str,
        query_embedding: np.ndarray,
        store: VectorStore,
        top_k: int = MAX_FINAL_K,
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Returns up to `top_k` (chunk, blended_score) tuples, sorted descending.
        """
        if not store.is_ready():
            return []

        # 1. Semantic candidates from FAISS
        semantic_k = min(SEMANTIC_TOP_K, store.chunk_count())
        semantic_results = store.search(query_embedding, top_k=semantic_k)
        if not semantic_results:
            return []

        # Build an id→score map for semantic (normalise 0-1)
        sem_max = max(s for _, s in semantic_results) or 1.0
        sem_scores: Dict[int, float] = {}
        chunk_map:  Dict[int, DocumentChunk] = {}
        for i, (chunk, score) in enumerate(semantic_results):
            sem_scores[i] = score / sem_max
            chunk_map[i]  = chunk

        # 2. Keyword (TF-IDF inspired) scoring
        query_terms = self._tokenise(query)
        kw_scores:  Dict[int, float] = {}
        for i, chunk in chunk_map.items():
            kw_scores[i] = self._keyword_score(query_terms, chunk.text)

        kw_max = max(kw_scores.values()) if kw_scores else 1.0
        if kw_max > 0:
            kw_scores = {k: v / kw_max for k, v in kw_scores.items()}

        # 3. Blend scores
        blended: List[Tuple[int, float]] = []
        for i in chunk_map:
            score = (SEMANTIC_WEIGHT * sem_scores.get(i, 0.0)
                     + KEYWORD_WEIGHT  * kw_scores.get(i, 0.0))
            if score >= MIN_SCORE_THRESH:
                blended.append((i, score))

        blended.sort(key=lambda x: x[1], reverse=True)

        # 4. Deduplicate near-identical text (keep highest scored)
        seen_prefixes: set = set()
        final = []
        for i, score in blended[:top_k * 2]:  # look at 2× budget
            chunk = chunk_map[i]
            prefix = chunk.text[:80].lower()
            if prefix not in seen_prefixes:
                seen_prefixes.add(prefix)
                final.append((chunk, score))
            if len(final) >= top_k:
                break

        return final

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _tokenise(text: str) -> List[str]:
        """Lowercase, split on non-alphanumeric, remove stop words."""
        STOPWORDS = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "about", "and", "but",
            "or", "nor", "so", "yet", "both", "either", "not", "no",
            "what", "how", "when", "where", "who", "which", "that",
            "this", "these", "those", "i", "me", "my", "we", "our",
            "you", "your", "he", "she", "it", "they", "their",
        }
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        return [t for t in tokens if t not in STOPWORDS and len(t) > 1]

    def _keyword_score(self, query_terms: List[str], doc_text: str) -> float:
        """
        TF-based score: for each query term, compute TF in the document,
        apply a log-normalised IDF approximation, return sum.
        Short documents are slightly penalised via length normalisation.
        """
        if not query_terms:
            return 0.0

        doc_terms = self._tokenise(doc_text)
        if not doc_terms:
            return 0.0

        doc_len   = len(doc_terms)
        term_freq: Dict[str, int] = {}
        for t in doc_terms:
            term_freq[t] = term_freq.get(t, 0) + 1

        score = 0.0
        for qt in query_terms:
            tf = term_freq.get(qt, 0)
            if tf > 0:
                # BM25-like TF saturation
                k1, b = 1.5, 0.75
                avg_len = 150  # approximate average chunk length in tokens
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))
                score += tf_norm

        # Phrase-level bonus: consecutive query terms appearing together
        query_phrase = " ".join(query_terms)
        doc_text_lower = doc_text.lower()
        # Check bigram matches
        for i in range(len(query_terms) - 1):
            bigram = query_terms[i] + " " + query_terms[i + 1]
            if bigram in doc_text_lower:
                score += 1.5  # strong bonus for phrase match

        return score
