# -*- coding: utf-8 -*-
"""
Rerank Engine for Vector Store.
Uses Cross-Encoders (via sentence_transformers) to rerank retrieval results.
Successor to rerank_service.py.
"""

import time
import torch
from functools import lru_cache
from typing import Dict, List, Tuple, Iterable, Optional, Any
from sentence_transformers import CrossEncoder

from llm_backend.utils.debug import trace
from llm_backend.utils.logger import logger

@lru_cache(maxsize=1)
def _get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


@lru_cache(maxsize=2)
def _load_model(model_name: str) -> CrossEncoder:
    """Reranker 모델을 지연 로드하고 캐싱합니다."""
    device = _get_device()
    trace(f"Loading Reranker model: {model_name} on {device}")
    try:
        model = CrossEncoder(model_name, device=device, max_length=512)
        logger.info(f"[Rerank] Model '{model_name}' loaded on {device}")
        return model
    except Exception as e:
        logger.error(f"[Rerank] Model load failed: {e}")
        raise


def rerank(
    query: str,
    docs: Iterable[Dict[str, Any]],
    model_name: str,
    top_k: int = 10,
    device: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """Cross-Encoder를 사용하여 문서의 순위를 재조정합니다."""
    start_time = time.perf_counter()
    
    try:
        model = _load_model(model_name)
    except Exception:
        return list(docs)[:top_k], {"load_s": 0.0, "rerank_s": 0.0}
    
    load_elapsed = time.perf_counter() - start_time

    docs_list = list(docs)
    if not docs_list:
        return [], {"load_s": load_elapsed, "rerank_s": 0.0}

    # Prepare query-doc pairs
    pairs = [(query, d.get("text", d.get("payload", {}).get("text", ""))) for d in docs_list]

    rerank_start = time.perf_counter()
    # CrossEncoder.predict handles batching automatically
    scores = model.predict(pairs, show_progress_bar=False)
    rerank_elapsed = time.perf_counter() - rerank_start

    reranked = []
    for i, d in enumerate(docs_list):
        s = float(scores[i])
        reranked.append({
            **d,
            "reranker_score": s,
            "score": s,
        })
    
    reranked.sort(key=lambda x: x["score"], reverse=True)
    
    timing = {
        "load_s": round(load_elapsed, 4),
        "rerank_s": round(rerank_elapsed, 4),
        "total_s": round(load_elapsed + rerank_elapsed, 4)
    }
    
    logger.debug(f"[Rerank] Completed for {len(docs_list)} docs in {timing['total_s']}s")
    return reranked[:top_k], timing
