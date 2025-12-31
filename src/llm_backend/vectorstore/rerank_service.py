"""Cross-encoder rerank service with caching and timing."""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Dict, Iterable, List, Tuple

import torch

from llm_backend.utils.debug import trace
from llm_backend.utils.logger import logger


from sentence_transformers import CrossEncoder

@lru_cache(maxsize=1)
def _get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

@lru_cache(maxsize=1)
def _load_model(model_name: str) -> CrossEncoder:
    device = _get_device()
    trace(f"Loading cross-encoder model: {model_name} on {device}")
    model = CrossEncoder(model_name, device=device, max_length=256)
    logger.info(f"[Rerank] Loaded cross-encoder '{model_name}' on {device}")
    return model


def rerank(
    query: str,
    docs: Iterable[Dict[str, str]],
    model_name: str,
    top_k: int,
    device: str = None,
) -> Tuple[List[Dict[str, str]], Dict[str, float]]:
    """Rerank documents with a cross-encoder and return timing metrics."""

    start = time.perf_counter()
    model = _load_model(model_name)
    load_elapsed = time.perf_counter() - start

    docs_list = list(docs)
    if not docs_list:
        return [], {"load_s": load_elapsed, "rerank_s": 0.0}

    pairs = [(query, d.get("text", "")) for d in docs_list]
    
    rerank_start = time.perf_counter()
    # CrossEncoder.predict handles tokenization and batching
    scores = model.predict(pairs, show_progress_bar=False)
    rerank_elapsed = time.perf_counter() - rerank_start

    reranked = [
        {
            "id": d.get("id"),
            "text": d.get("text"),
            "title": d.get("title"),
            "score": float(scores[i]),
        }
        for i, d in enumerate(docs_list)
    ]
    reranked.sort(key=lambda x: x["score"], reverse=True)

    return reranked[:top_k], {"load_s": load_elapsed, "rerank_s": rerank_elapsed}
