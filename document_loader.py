"""
document_loader.py
Loads and chunks documents from uploaded files (in-memory, no filesystem dependency).
Supports: PDF, TXT, DOCX
"""

import io
import re
from dataclasses import dataclass
from typing import List


@dataclass
class DocumentChunk:
    text: str
    source: str
    page: int


def load_and_chunk(file_bytes: bytes, filename: str, chunk_size: int = 500, overlap: int = 50) -> List[DocumentChunk]:
    """
    Load a file from bytes and return a list of DocumentChunks.
    """
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        pages = _load_pdf(file_bytes)
    elif ext == "txt":
        pages = _load_txt(file_bytes)
    elif ext == "docx":
        pages = _load_docx(file_bytes)
    else:
        return []

    chunks = []
    for page_num, text in enumerate(pages, start=1):
        page_chunks = _chunk_text(text, chunk_size, overlap)
        for chunk in page_chunks:
            if chunk.strip():
                chunks.append(DocumentChunk(text=chunk.strip(), source=filename, page=page_num))

    return chunks


def _load_pdf(file_bytes: bytes) -> List[str]:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return pages
    except Exception as e:
        return [f"[Error reading PDF: {e}]"]


def _load_txt(file_bytes: bytes) -> List[str]:
    try:
        text = file_bytes.decode("utf-8", errors="replace")
        return [text]
    except Exception as e:
        return [f"[Error reading TXT: {e}]"]


def _load_docx(file_bytes: bytes) -> List[str]:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return [full_text]
    except Exception as e:
        return [f"[Error reading DOCX: {e}]"]


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks
