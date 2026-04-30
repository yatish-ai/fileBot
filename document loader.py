"""
document_loader.py
Loads and chunks documents from uploaded files (in-memory, no filesystem dependency).
Supports: PDF, TXT, DOCX
v2: Sentence-boundary-aware chunking, smaller chunks, section detection.
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


def load_and_chunk(
    file_bytes: bytes,
    filename: str,
    chunk_size: int = 200,   # words per chunk (reduced from 500)
    overlap: int = 40,        # overlap in words (was 50)
) -> List[DocumentChunk]:
    """
    Load a file from bytes and return a list of DocumentChunks.
    Uses sentence-boundary-aware splitting to avoid mid-sentence breaks.
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
        # Normalise whitespace
        text = re.sub(r"\s+", " ", text).strip()
        page_chunks = _chunk_text_sentence_aware(text, chunk_size, overlap)
        for chunk in page_chunks:
            if chunk.strip():
                chunks.append(DocumentChunk(text=chunk.strip(), source=filename, page=page_num))

    return chunks


# ── Loaders ───────────────────────────────────────────────────────────────────

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


# ── Chunking ──────────────────────────────────────────────────────────────────

def _split_sentences(text: str) -> List[str]:
    """
    Split text into sentences using a simple but robust regex.
    Avoids splitting on abbreviations like 'Mr.', 'Ph.D.', decimal numbers.
    """
    # Sentence boundary: period/!? followed by space and uppercase, or newline
    sentence_endings = re.compile(
        r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s+(?=[A-Z])|(?<=\n)"
    )
    raw = sentence_endings.split(text)
    # Further split on hard newlines that separate sections (common in resumes/reports)
    sentences = []
    for s in raw:
        sub = [x.strip() for x in s.split("\n") if x.strip()]
        sentences.extend(sub)
    return sentences


def _chunk_text_sentence_aware(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into overlapping chunks that respect sentence boundaries.
    Each chunk targets `chunk_size` words with `overlap` words of context.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return []

    # Convert sentences to word lists for counting
    sent_words = [s.split() for s in sentences]

    chunks = []
    current_words: List[str] = []
    current_sents: List[List[str]] = []   # track sentence groupings

    for sw in sent_words:
        current_words.extend(sw)
        current_sents.append(sw)

        if len(current_words) >= chunk_size:
            chunk_text = " ".join(current_words)
            chunks.append(chunk_text)

            # Overlap: rewind by keeping last `overlap` words worth of sentences
            overlap_words: List[str] = []
            overlap_sents: List[List[str]] = []
            for s in reversed(current_sents):
                if len(overlap_words) + len(s) <= overlap:
                    overlap_words = s + overlap_words
                    overlap_sents.insert(0, s)
                else:
                    break
            current_words = list(overlap_words)
            current_sents = list(overlap_sents)

    # Flush remaining text as a final chunk
    if current_words:
        chunk_text = " ".join(current_words)
        # Only add if it's substantially new (not pure overlap)
        if not chunks or chunk_text != chunks[-1]:
            chunks.append(chunk_text)

    return chunks
