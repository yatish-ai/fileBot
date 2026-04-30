"""
query_rewriter.py
Query understanding and rewriting layer for FileBOT.
Resolves references, expands vague terms, converts follow-ups to standalone queries.
Uses a lightweight rule-based engine with an optional LLM-based rewrite.
"""

import re
from typing import Optional


# ── Follow-up / elaboration intent signals ────────────────────────────────────

ELABORATION_TRIGGERS = {
    "elaborate", "explain more", "tell me more", "go on", "expand",
    "more detail", "more details", "in detail", "detail", "details",
    "give more", "keep going", "continue", "and then", "what else",
    "say more", "elaborate on that", "can you expand",
}

SUMMARY_TRIGGERS = {
    "summarize", "summary", "give me a summary", "brief overview",
    "overview", "tldr", "tl;dr", "in brief", "short version",
    "key points", "main points", "highlights",
}

COMPARISON_TRIGGERS = {
    "compare", "comparison", "difference", "differences", "vs", "versus",
    "contrast", "how do they differ", "what's the difference",
    "which is better", "pros and cons",
}

EXTRACTION_TRIGGERS = {
    "list", "what are", "give me all", "show all", "extract",
    "find all", "enumerate", "what is the", "what's the",
    "phone", "email", "contact", "address", "name", "skills",
    "experience", "education", "projects",
}

# Pronoun / vague reference patterns → needs prior context
REFERENCE_PATTERNS = re.compile(
    r"\b(it|this|that|they|them|those|these|he|she|his|her|their|its|"
    r"the above|the same|aforementioned)\b",
    re.IGNORECASE,
)

# Common domain expansions (resume/doc specific)
DOMAIN_EXPANSIONS = {
    r"\bmobile\b":        "mobile phone number",
    r"\bphone\b":         "phone number contact",
    r"\bemail\b":         "email address contact",
    r"\baddress\b":       "address location contact",
    r"\bskills\b":        "technical skills expertise competencies",
    r"\bprojects?\b":     "projects work experience portfolio",
    r"\beducation\b":     "education qualification degree university",
    r"\bexperience\b":    "work experience job employment history",
    r"\bcgpa\b":          "CGPA GPA academic score grade",
    r"\blinkedin\b":      "LinkedIn profile social media URL link",
    r"\bgithub\b":        "GitHub profile repository code link",
    r"\bsummary\b(?! of)":"professional summary about section",
}


class QueryRewriter:
    """
    Rewrites / enhances user queries before retrieval.
    Works entirely rule-based; no additional LLM call required.
    """

    def rewrite(
        self,
        query: str,
        last_answer: Optional[str] = None,
        last_query: Optional[str] = None,
    ) -> str:
        """
        Main entry point.
        Returns a rewritten, standalone query optimised for vector retrieval.
        """
        original = query.strip()
        q = original.lower().strip()

        # 1. Detect and handle elaboration / follow-up intent
        if self._is_elaboration(q):
            if last_answer and last_query:
                # Build a standalone query from prior context
                rewritten = f"Explain in more detail: {last_query}"
                return rewritten
            elif last_query:
                return f"More details about: {last_query}"
            # No prior context — return as-is
            return original

        # 2. Detect pronoun / reference-heavy queries
        if REFERENCE_PATTERNS.search(q) and last_query:
            resolved = self._resolve_references(original, last_query)
            q = resolved.lower()
            original = resolved

        # 3. Domain expansion for short / vague queries
        expanded = self._expand_domain_terms(original)

        # 4. Append prior query context for short follow-ups
        if len(expanded.split()) <= 5 and last_query:
            expanded = f"{expanded} (context: {last_query})"

        return expanded

    def detect_intent(self, query: str) -> str:
        """
        Returns a high-level intent tag for downstream prompt shaping.
        One of: 'elaboration' | 'summarize' | 'compare' | 'extract' | 'general'
        """
        q = query.lower()
        if self._is_elaboration(q):
            return "elaboration"
        if any(t in q for t in SUMMARY_TRIGGERS):
            return "summarize"
        if any(t in q for t in COMPARISON_TRIGGERS):
            return "compare"
        if any(t in q for t in EXTRACTION_TRIGGERS):
            return "extract"
        return "general"

    # ── Private ───────────────────────────────────────────────────────────────

    def _is_elaboration(self, q: str) -> bool:
        return any(t in q for t in ELABORATION_TRIGGERS)

    def _resolve_references(self, query: str, last_query: str) -> str:
        """Replace vague pronouns with a reference to the prior topic."""
        # Strip trailing punctuation from last query for cleaner embedding
        topic = last_query.rstrip("?.,!")
        # Replace the most common anaphoric patterns
        resolved = re.sub(
            r"\b(it|this|that|they|them|those|these)\b",
            topic,
            query,
            flags=re.IGNORECASE,
            count=1,
        )
        return resolved

    def _expand_domain_terms(self, query: str) -> str:
        """Expand known short/vague domain terms for better semantic matching."""
        expanded = query
        for pattern, replacement in DOMAIN_EXPANSIONS.items():
            # Only expand if the replacement adds value (avoid ballooning long queries)
            if len(query.split()) <= 8:
                expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
        return expanded


# ── Optional LLM-based rewriter (uses Groq, only called when rule-based is weak) ──

def llm_rewrite_query(
    query: str,
    last_query: Optional[str],
    last_answer: Optional[str],
    groq_api_key: str,
) -> Optional[str]:
    """
    Use the LLM to rewrite a query into a standalone, self-contained question.
    Only call this when the query is highly context-dependent and rule-based
    rewriting is insufficient (e.g. complex multi-turn references).
    Returns None on failure so caller can fall back to rule-based rewrite.
    """
    import requests

    if not groq_api_key:
        return None

    history_snippet = ""
    if last_query:
        history_snippet += f"Previous question: {last_query}\n"
    if last_answer:
        snippet = last_answer[:300] + "…" if len(last_answer) > 300 else last_answer
        history_snippet += f"Previous answer (excerpt): {snippet}\n"

    system = (
        "You are a query rewriter. Given a conversation history and a follow-up question, "
        "rewrite the follow-up as a fully self-contained search query. "
        "Output ONLY the rewritten query — no explanation, no quotes, no preamble."
    )
    user_msg = (
        f"{history_snippet}"
        f"Follow-up question: {query}\n\n"
        "Rewritten standalone query:"
    )

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                "max_tokens": 80,
                "temperature": 0.0,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            choices = resp.json().get("choices", [])
            if choices:
                rewritten = choices[0]["message"]["content"].strip().strip('"').strip("'")
                # Sanity check: must be reasonably short and non-empty
                if rewritten and len(rewritten) < 300:
                    return rewritten
    except Exception:
        pass

    return None
