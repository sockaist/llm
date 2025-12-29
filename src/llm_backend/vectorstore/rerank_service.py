"""Cross-encoder rerank service with caching and timing."""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Dict, Iterable, List, Tuple

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from llm_backend.utils.debug import trace
from llm_backend.utils.logger import logger


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> Tuple[AutoTokenizer, AutoModelForSequenceClassification]:
    trace(f"Loading cross-encoder model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    logger.info(f"[Rerank] Loaded cross-encoder '{model_name}'")
    return tokenizer, model


def rerank(
    query: str,
    docs: Iterable[Dict[str, str]],
    model_name: str,
    top_k: int,
    device: str = "cpu",
) -> Tuple[List[Dict[str, str]], Dict[str, float]]:
    """Rerank documents with a cross-encoder and return timing metrics."""

    start = time.perf_counter()
    tokenizer, model = _load_model(model_name)
    load_elapsed = time.perf_counter() - start

    docs_list = list(docs)
    if not docs_list:
        return [], {"load_s": load_elapsed, "rerank_s": 0.0}

    pairs = [(query, d.get("text", "")) for d in docs_list]
    inputs = tokenizer(
        [q for q, _ in pairs],
        [d for _, d in pairs],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    ).to(device)

    rerank_start = time.perf_counter()
    with torch.no_grad():
        scores = model(**inputs).logits.squeeze(-1).cpu().numpy()
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
