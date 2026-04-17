# FileBOT — Your Smart File Assistant

A production-ready RAG app built with Streamlit, sentence-transformers, FAISS, and Groq.

## Flow

```
UPLOAD → PROCESS → CHAT
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your Groq API key
Get a free key at https://console.groq.com

**Local:**
```bash
export GROQ_API_KEY=your_key_here
streamlit run app.py
```

**Streamlit Cloud:**
Add `GROQ_API_KEY` in App Settings → Secrets:
```toml
GROQ_API_KEY = "your_key_here"
```

**HuggingFace Spaces:**
Add `GROQ_API_KEY` in Settings → Repository Secrets.

## Project Structure

```
app.py              ← Streamlit UI (Upload → Process → Chat)
rag_pipeline.py     ← Orchestrates document processing and Q&A
document_loader.py  ← PDF/TXT/DOCX loading and chunking (in-memory)
embeddings.py       ← Sentence-transformer embeddings with caching
vector_store.py     ← FAISS in-memory index + search
requirements.txt    ← Pinned dependencies
```

## Tech Stack

| Component    | Library                         |
|--------------|---------------------------------|
| UI           | Streamlit                       |
| Embeddings   | sentence-transformers (MiniLM)  |
| Vector Store | faiss-cpu                       |
| LLM          | Groq API (LLaMA3-8B)            |
| PDF parsing  | pypdf                           |
| DOCX parsing | python-docx                     |

## Notes

- All document processing is done **in-memory** (no temp files written)
- Embedding model (`all-MiniLM-L6-v2`) is downloaded once and cached
- Works on Streamlit Cloud's free tier (512MB RAM)
- Chat is disabled until documents are processed
- Retry logic on empty LLM responses
