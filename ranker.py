"""
ranker.py
Re-ranks retrieved (chunk, score) candidates using multiple signals:
  • Coverage: how many unique query terms appear in the chunk
  • Density: query term density (matches / total tokens)
  • Recency bias: earlier chunks in a document can be upweighted for summaries
  • Score passthrough from retriever
Returns a re-ordered list, trimmed to `final_k`.
"""

import re
from typing import List, Tuple

from document_loader import DocumentChunk


# Stopword set (reused from retriever for consistency)
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "and", "but", "or", "not",
    "what", "how", "when", "where", "who", "which", "that", "this",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "their",
}


def _tokenise(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


class Ranker:
    """
    Cross-encoder–free re-ranker using heuristic coverage + density signals.
    Fast and dependency-free; good enough for document Q&A accuracy.
    """

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[DocumentChunk, float]],
        final_k: int = 5,
        intent: str = "general",
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Re-rank candidates and return top `final_k`.

        Args:
            query      : original (or rewritten) user query
            candidates : list of (DocumentChunk, retrieval_score) from retriever
            final_k    : how many to return
            intent     : 'general' | 'summarize' | 'compare' | 'extract' | 'elaboration'
        """
        if not candidates:
            return []

        query_terms = set(_tokenise(query))
        scored = []

        for chunk, retrieval_score in candidates:
            doc_terms = _tokenise(chunk.text)
            doc_set   = set(doc_terms)
            doc_len   = max(len(doc_terms), 1)

            # Signal 1: term coverage — fraction of query terms present
            coverage = len(query_terms & doc_set) / max(len(query_terms), 1)

            # Signal 2: density — matched query terms per total doc tokens
            matched_count = sum(1 for t in doc_terms if t in query_terms)
            density = matched_count / doc_len

            # Signal 3: title / header bonus — chunk contains capitalised keywords
            header_bonus = self._header_bonus(chunk.text, query_terms)

            # Signal 4: intent-specific bonuses
            intent_bonus = self._intent_bonus(chunk.text, intent)

            # Combine into a re-rank score (weights tuned empirically)
            rerank_score = (
                0.50 * retrieval_score
                + 0.20 * coverage
                + 0.10 * density
                + 0.10 * header_bonus
                + 0.10 * intent_bonus
            )

            scored.append((chunk, rerank_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:final_k]

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _header_bonus(text: str, query_terms: set) -> float:
        """Bonus if the chunk starts with a header-like line containing query terms."""
        first_line = text.split("\n")[0][:120].lower()
        matches = sum(1 for t in query_terms if t in first_line)
        return min(matches / max(len(query_terms), 1), 1.0)

    @staticmethod
    def _intent_bonus(text: str, intent: str) -> float:
        """Apply small bonuses based on query intent signals in the chunk text."""
        text_lower = text.lower()

        if intent == "summarize":
            markers = ["summary", "overview", "introduction", "objective", "about"]
        elif intent == "compare":
            markers = ["compared", "versus", "difference", "whereas", "while", "unlike"]
        elif intent == "extract":
            # Extraction queries benefit from chunks with structured data
            markers = [":", "@", "+91", "http", "github", "linkedin", "•", "-"]
        elif intent == "elaboration":
            # Prefer longer, explanation-rich chunks
            return min(len(text) / 1500, 1.0)
        else:
            return 0.0

        hits = sum(1 for m in markers if m in text_lower)
        return min(hits / max(len(markers), 1), 1.0)
