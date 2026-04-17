"""
rag_pipeline.py
Core RAG pipeline: document processing and question answering via Groq API.
"""

import os
import json
import requests
from typing import List, Tuple, Dict, Any

from document_loader import load_and_chunk, DocumentChunk
from embeddings import embed_texts, embed_query
from vector_store import VectorStore


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"
MAX_CONTEXT_CHUNKS = 4
RETRY_ONCE = True


def process_documents(uploaded_files: List[Dict[str, Any]]) -> Tuple[VectorStore, int]:
    """
    Process uploaded files into a VectorStore.

    Args:
        uploaded_files: list of dicts with keys 'name' (str) and 'bytes' (bytes)

    Returns:
        (VectorStore, total_chunk_count)
    """
    all_chunks: List[DocumentChunk] = []

    for f in uploaded_files:
        chunks = load_and_chunk(f["bytes"], f["name"])
        all_chunks.extend(chunks)

    if not all_chunks:
        raise ValueError("No text could be extracted from the uploaded files.")

    texts = [c.text for c in all_chunks]
    embeddings = embed_texts(texts)

    store = VectorStore()
    store.build(all_chunks, embeddings)

    return store, len(all_chunks)


def answer_question(question: str, store: VectorStore) -> Dict[str, Any]:
    """
    Retrieve relevant chunks and query Groq LLM.

    Returns dict with:
        - answer (str)
        - sources (list of dicts with 'source' and 'page')
        - error (str or None)
    """
    if not store.is_ready():
        return {
            "answer": "Please upload and process documents before asking questions.",
            "sources": [],
            "error": None
        }

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return {
            "answer": "⚠️ No GROQ_API_KEY found. Please set your API key in environment variables.",
            "sources": [],
            "error": "missing_api_key"
        }

    # Retrieve top chunks
    q_emb = embed_query(question)
    results = store.search(q_emb, top_k=MAX_CONTEXT_CHUNKS)

    if not results:
        return {
            "answer": "No relevant content found in the documents.",
            "sources": [],
            "error": None
        }

    context = "\n\n---\n\n".join([
        f"[Source: {chunk.source}, Page {chunk.page}]\n{chunk.text}"
        for chunk, _ in results
    ])

    sources = [
        {"source": chunk.source, "page": chunk.page}
        for chunk, _ in results
    ]

    prompt = f"""You are a helpful assistant. Answer the question based strictly on the provided context.
If the answer is not in the context, say "I couldn't find relevant information in the documents."

Context:
{context}

Question: {question}

Answer:"""

    answer = _call_groq(api_key, prompt)

    # Retry once on empty response
    if not answer and RETRY_ONCE:
        answer = _call_groq(api_key, prompt)

    if not answer:
        answer = "The model returned an empty response. Please try rephrasing your question."

    return {
        "answer": answer,
        "sources": sources,
        "error": None
    }


def _call_groq(api_key: str, prompt: str) -> str:
    """Call the Groq API and return the response text."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": 0.2
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)

        if resp.status_code == 401:
            return "⚠️ Invalid API key. Please check your GROQ_API_KEY."
        if resp.status_code == 429:
            return "⚠️ Rate limit reached. Please wait a moment and try again."
        if resp.status_code != 200:
            return f"⚠️ API error (status {resp.status_code}). Please try again."

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return ""

        return choices[0].get("message", {}).get("content", "").strip()

    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "⚠️ Could not connect to the API. Check your internet connection."
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"
