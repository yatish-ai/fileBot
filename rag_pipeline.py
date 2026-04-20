"""
rag_pipeline.py
Core RAG pipeline: document processing and question answering via Groq API.
Supports incremental merging of new files into an existing VectorStore.
"""

import os
import requests
from typing import List, Tuple, Dict, Any, Optional

from document_loader import load_and_chunk, DocumentChunk
from embeddings import embed_texts, embed_query
from vector_store import VectorStore


GROQ_API_URL       = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL         = "llama-3.1-8b-instant"
MAX_CONTEXT_CHUNKS = 3
MAX_CHUNK_WORDS    = 200
MAX_PROMPT_CHARS   = 6000
MAX_TOKENS_OUT     = 512
RETRY_ONCE         = True


def process_documents(
    uploaded_files: List[Dict[str, Any]],
    existing_store: Optional[VectorStore] = None
) -> Tuple[VectorStore, int, int]:
    """
    Process uploaded files and merge into an existing VectorStore (or build fresh).

    Args:
        uploaded_files : list of {'name': str, 'bytes': bytes}
        existing_store : existing VectorStore to merge into, or None for fresh build

    Returns:
        (store, new_chunks_added, total_chunks)
    """
    all_new_chunks: List[DocumentChunk] = []

    for f in uploaded_files:
        chunks = load_and_chunk(f["bytes"], f["name"])
        all_new_chunks.extend(chunks)

    if not all_new_chunks:
        raise ValueError("No text could be extracted from the uploaded files.")

    texts      = [c.text for c in all_new_chunks]
    embeddings = embed_texts(texts)

    if existing_store is None or not existing_store.is_ready():
        store = VectorStore()
        store.build(all_new_chunks, embeddings)
        new_added = len(all_new_chunks)
    else:
        store     = existing_store
        new_added = store.merge(all_new_chunks, embeddings)

    return store, new_added, store.chunk_count()


def answer_question(question: str, store: VectorStore) -> Dict[str, Any]:
    """Retrieve relevant chunks and query Groq LLM."""
    if not store.is_ready():
        return {"answer": "Please upload and process documents before asking questions.",
                "sources": [], "error": None}

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return {"answer": "⚠️ No GROQ_API_KEY found. Please set it in Spaces secrets.",
                "sources": [], "error": "missing_api_key"}

    q_emb   = embed_query(question)
    results = store.search(q_emb, top_k=MAX_CONTEXT_CHUNKS)

    if not results:
        return {"answer": "No relevant content found in the documents.",
                "sources": [], "error": None}

    def _trim(text: str) -> str:
        words = text.split()
        return " ".join(words[:MAX_CHUNK_WORDS]) if len(words) > MAX_CHUNK_WORDS else text

    context = "\n\n---\n\n".join(
        f"[Source: {c.source}, Page {c.page}]\n{_trim(c.text)}"
        for c, _ in results
    )
    sources = [{"source": c.source, "page": c.page} for c, _ in results]

    prompt = (
        "You are FileBOT, a helpful document assistant. "
        "Answer the question based strictly on the provided context. "
        "If the answer is not in the context, say: "
        "\"I couldn't find relevant information in the documents.\"\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\nAnswer:"
    )[:MAX_PROMPT_CHARS]

    answer = _call_groq(api_key, prompt)
    if not answer and RETRY_ONCE:
        answer = _call_groq(api_key, prompt)
    if not answer:
        answer = "FileBOT returned an empty response. Please try rephrasing your question."

    return {"answer": answer, "sources": sources, "error": None}


def _call_groq(api_key: str, prompt: str) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": MAX_TOKENS_OUT, "temperature": 0.2}
    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)

        if resp.status_code == 401:
            return "⚠️ Invalid API key. Please check your GROQ_API_KEY in Spaces secrets."
        if resp.status_code == 429:
            return "⚠️ Rate limit reached. Please wait a moment and try again."
        if resp.status_code in (400, 422):
            try:    detail = resp.json().get("error", {}).get("message", resp.text[:300])
            except: detail = resp.text[:300]
            return f"⚠️ Groq rejected the request: {detail}"
        if resp.status_code != 200:
            try:    detail = resp.json().get("error", {}).get("message", resp.text[:300])
            except: detail = resp.text[:300]
            return f"⚠️ Groq API error ({resp.status_code}): {detail}"

        choices = resp.json().get("choices", [])
        return choices[0].get("message", {}).get("content", "").strip() if choices else ""

    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "⚠️ Could not connect to Groq API. Check your internet connection."
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"