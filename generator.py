"""
generator.py
Context-aware answer generation for FileBOT.
Builds intent-shaped prompts and calls the Groq LLM.
Handles conversational memory injection and robust error handling.
"""

import os
import requests
from typing import List, Tuple, Dict, Any, Optional

from document_loader import DocumentChunk


# ── Constants ─────────────────────────────────────────────────────────────────
GROQ_API_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL      = "llama-3.1-8b-instant"
MAX_TOKENS_OUT  = 768
MAX_CHUNK_WORDS = 220
MAX_PROMPT_CHARS = 7000
TEMPERATURE     = 0.25


# ── Intent-specific prompt fragments ─────────────────────────────────────────

_INTENT_INSTRUCTIONS = {
    "summarize": (
        "The user wants a concise summary. Provide a structured summary with "
        "key points as bullet points. Cover all major sections present in the context."
    ),
    "compare": (
        "The user wants a comparison. Use a structured format: present similarities "
        "and differences clearly, ideally as a short table or labelled sections."
    ),
    "extract": (
        "The user wants specific information extracted. Provide the exact values "
        "requested (names, numbers, links, dates) in a clear, scannable format. "
        "If multiple items are requested, list each one explicitly."
    ),
    "elaboration": (
        "The user wants more detail on a previous answer. Expand on the topic, "
        "add context, examples, or explanations. Build on what was said before."
    ),
    "general": (
        "Answer the question thoroughly. Use bullet points or numbered lists if "
        "multiple items are relevant. Provide concrete details from the context."
    ),
}

_BASE_SYSTEM = """You are FileBOT, an intelligent document assistant.
You answer questions strictly based on the provided document context.
Rules:
- Always be specific and cite details from the context.
- If the answer is partially present, give what you can and note what's missing.
- If the answer is truly absent, say: "I couldn't find this information in the uploaded documents."
- For follow-ups or vague queries, use the conversation history to understand intent.
- Format responses clearly: use bullet points for lists, headers for sections.
- Never fabricate information not present in the context.
"""


class Generator:
    """
    Builds prompts and calls Groq LLM to generate answers.
    """

    def generate(
        self,
        question: str,
        rewritten_query: str,
        chunks: List[Tuple[DocumentChunk, float]],
        conversation_history: str,
        intent: str = "general",
        last_answer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate an answer from retrieved chunks.

        Returns:
            {
              'answer': str,
              'sources': [{'source': str, 'page': int}],
              'error': str | None
            }
        """
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            return {
                "answer": "⚠️ No GROQ_API_KEY found. Please set it in Spaces secrets.",
                "sources": [],
                "error": "missing_api_key",
            }

        if not chunks:
            return {
                "answer": (
                    "I couldn't find relevant information in the documents for your question. "
                    "Try rephrasing or uploading more relevant files."
                ),
                "sources": [],
                "error": None,
            }

        # Build context block
        context_parts = []
        sources = []
        for chunk, score in chunks:
            trimmed = self._trim(chunk.text)
            context_parts.append(
                f"[Source: {chunk.source} | Page {chunk.page} | Relevance: {score:.2f}]\n{trimmed}"
            )
            sources.append({"source": chunk.source, "page": chunk.page})

        context_str = "\n\n---\n\n".join(context_parts)

        # Build intent instruction
        intent_instr = _INTENT_INSTRUCTIONS.get(intent, _INTENT_INSTRUCTIONS["general"])

        # Conversation history block
        history_block = ""
        if conversation_history:
            history_block = (
                f"\n\n=== Conversation History ===\n{conversation_history}\n"
                "=== End of History ===\n"
            )

        # Previous answer block (for elaboration)
        prev_block = ""
        if intent == "elaboration" and last_answer:
            excerpt = last_answer[:500] + "…" if len(last_answer) > 500 else last_answer
            prev_block = f"\n\n=== Previous Answer (for elaboration) ===\n{excerpt}\n"

        # Assemble the user message
        user_message = (
            f"{history_block}"
            f"{prev_block}"
            f"\n=== Document Context ===\n{context_str}\n"
            f"=== End of Context ===\n\n"
            f"Task instruction: {intent_instr}\n\n"
            f"User's original question: {question}\n"
            + (f"(Interpreted as: {rewritten_query})\n" if rewritten_query != question else "")
            + "\nAnswer:"
        )

        # Truncate to avoid overflow
        user_message = user_message[:MAX_PROMPT_CHARS]

        answer = self._call_groq(api_key, user_message)
        if not answer:
            # Single retry
            answer = self._call_groq(api_key, user_message)
        if not answer:
            answer = (
                "FileBOT returned an empty response. "
                "Please try rephrasing your question."
            )

        # Deduplicate sources
        seen = set()
        unique_sources = []
        for s in sources:
            key = (s["source"], s["page"])
            if key not in seen:
                seen.add(key)
                unique_sources.append(s)

        return {"answer": answer, "sources": unique_sources, "error": None}

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _trim(text: str) -> str:
        words = text.split()
        return " ".join(words[:MAX_CHUNK_WORDS]) if len(words) > MAX_CHUNK_WORDS else text

    @staticmethod
    def _call_groq(api_key: str, user_message: str) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": _BASE_SYSTEM},
                {"role": "user",   "content": user_message},
            ],
            "max_tokens": MAX_TOKENS_OUT,
            "temperature": TEMPERATURE,
        }
        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)

            if resp.status_code == 401:
                return "⚠️ Invalid API key. Please check your GROQ_API_KEY."
            if resp.status_code == 429:
                return "⚠️ Rate limit reached. Please wait a moment and try again."
            if resp.status_code in (400, 422):
                detail = _safe_error(resp)
                return f"⚠️ Groq rejected the request: {detail}"
            if resp.status_code != 200:
                detail = _safe_error(resp)
                return f"⚠️ Groq API error ({resp.status_code}): {detail}"

            choices = resp.json().get("choices", [])
            return choices[0].get("message", {}).get("content", "").strip() if choices else ""

        except requests.exceptions.Timeout:
            return "⚠️ Request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            return "⚠️ Could not connect to Groq API. Check your internet connection."
        except Exception as e:
            return f"⚠️ Unexpected error: {str(e)}"


def _safe_error(resp) -> str:
    try:
        return resp.json().get("error", {}).get("message", resp.text[:300])
    except Exception:
        return resp.text[:300]
