"""
rag_pipeline.py  (v2)
Orchestrates the advanced RAG pipeline:
  document processing → query rewriting → hybrid retrieval → re-ranking → generation
Supports incremental file merging and full conversational memory.
"""

from typing import List, Dict, Any, Optional, Tuple

from document_loader import load_and_chunk, DocumentChunk
from embeddings import embed_texts, embed_query
from vector_store import VectorStore
from memory_manager import MemoryManager
from query_rewriter import QueryRewriter
from retriever import HybridRetriever
from ranker import Ranker
from generator import Generator


# ── Module singletons (stateless — safe to reuse across calls) ────────────────
_rewriter  = QueryRewriter()
_retriever = HybridRetriever()
_ranker    = Ranker()
_generator = Generator()


# ══════════════════════════════════════════════════════════════════════════════
# Document Processing
# ══════════════════════════════════════════════════════════════════════════════

def process_documents(
    uploaded_files: List[Dict[str, Any]],
    existing_store: Optional[VectorStore] = None,
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


# ══════════════════════════════════════════════════════════════════════════════
# Question Answering
# ══════════════════════════════════════════════════════════════════════════════

def answer_question(
    question: str,
    store: VectorStore,
    memory: Optional[MemoryManager] = None,
) -> Dict[str, Any]:
    """
    Full advanced RAG pipeline:
      1. Query rewriting (reference resolution + expansion)
      2. Hybrid retrieval (semantic + keyword)
      3. Re-ranking
      4. Context-aware generation with memory injection

    Args:
        question : raw user question
        store    : populated VectorStore
        memory   : MemoryManager instance (shared across turns by the caller)

    Returns:
        {'answer': str, 'sources': list, 'error': str|None,
         'rewritten_query': str, 'intent': str}
    """
    if not store.is_ready():
        return {
            "answer":   "Please upload and process documents before asking questions.",
            "sources":  [],
            "error":    None,
            "rewritten_query": question,
            "intent":   "general",
        }

    # 1. Memory context
    last_query  = memory.get_last_user_query()     if memory else None
    last_answer = memory.get_last_assistant_answer() if memory else None
    history_str = memory.get_history_for_prompt()   if memory else ""

    # 2. Query rewriting
    rewritten = _rewriter.rewrite(
        question,
        last_answer=last_answer,
        last_query=last_query,
    )
    intent = _rewriter.detect_intent(question)

    # 3. Embed rewritten query
    q_embedding = embed_query(rewritten)

    # 4. Hybrid retrieval
    candidates = _retriever.retrieve(
        query=rewritten,
        query_embedding=q_embedding,
        store=store,
        top_k=8,
    )

    # 5. Re-rank
    ranked = _ranker.rerank(
        query=rewritten,
        candidates=candidates,
        final_k=5,
        intent=intent,
    )

    # 6. Generate answer
    result = _generator.generate(
        question=question,
        rewritten_query=rewritten,
        chunks=ranked,
        conversation_history=history_str,
        intent=intent,
        last_answer=last_answer,
    )

    # 7. Update memory (caller must pass the same MemoryManager every turn)
    if memory:
        memory.add_turn("user",      question)
        memory.add_turn("assistant", result["answer"], sources=result["sources"])

    result["rewritten_query"] = rewritten
    result["intent"]          = intent
    return result
