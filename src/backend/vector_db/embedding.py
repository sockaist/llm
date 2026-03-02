import re
from functools import lru_cache
from typing import List, Tuple

from openai import OpenAI

try:
    from .config import (
        OPENAI_API_KEY,
        OPENAI_EMBEDDING_MODEL,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
    )
except ImportError:
    from config import (  # type: ignore
        OPENAI_API_KEY,
        OPENAI_EMBEDDING_MODEL,
        CHUNK_SIZE,
        CHUNK_OVERLAP,
    )


def _get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=OPENAI_API_KEY)


def _split_long_text(text: str, max_chars: int, overlap: int) -> List[str]:
    chunks: List[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(text_len, start + max_chars)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == text_len:
            break
        start = max(0, end - overlap)

    return chunks


def split_text(text: str, max_chars: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    if not text or not text.strip():
        return []

    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return [normalized]

    sentences = re.split(r"(?<=[.!?。！？])\s+", normalized)
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        if not sentence:
            continue

        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = sentence
        else:
            chunks.extend(_split_long_text(sentence, max_chars=max_chars, overlap=overlap))
            current = ""

    if current:
        chunks.append(current)

    if not chunks:
        return _split_long_text(normalized, max_chars=max_chars, overlap=overlap)
    return chunks


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    client = _get_client()
    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def embed_query(text: str) -> List[float]:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return []
    return list(_embed_query_cached(normalized))


@lru_cache(maxsize=512)
def _embed_query_cached(normalized_text: str) -> Tuple[float, ...]:
    vectors = embed_texts([normalized_text])
    if not vectors:
        return tuple()
    return tuple(vectors[0])


def content_embedder(text: str) -> List[Tuple[str, List[float]]]:
    chunks = split_text(text)
    if not chunks:
        return []

    vectors = embed_texts(chunks)
    return list(zip(chunks, vectors))
