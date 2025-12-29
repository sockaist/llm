"""Hybrid search pipeline orchestration for VectorDBManager.

Keeps the previous behavior (dense + BM25 + SPLADE → fusion → dedup → optional
cross-encoder rerank) but separates the orchestration from the manager class
for readability and testability.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from qdrant_client.models import Filter, FieldCondition, MatchValue

from llm_backend.utils.debug import trace
from llm_backend.utils.logger import logger
from llm_backend.vectorstore.rerank_service import rerank as rerank_service
from llm_backend.vectorstore.reranker_module import (
    deduplicate_and_average as dedup_avg_by_doc,
    weighted_fuse,
)


def run_query_pipeline(
    manager,
    query_text: str,
    top_k: int,
    collections: List[str],
    cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Execute the hybrid search pipeline using the provided manager.

    Args:
        manager: VectorDBManager instance
        query_text: user query
        top_k: result limit
        collections: list of collection names
        cfg: pipeline_config dict on the manager
    """

    trace(f"pipeline.query('{query_text[:20]}...')")

    merged: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    # 1) per-collection search and fusion
    for col in collections:
        dense_res, sparse_res, splade_res = manager._search_collection_unique(
            col,
            query_text,
            top_k,
            cfg["use_dense"],
            cfg["use_sparse"],
            cfg["use_splade"],
        )

        fused = weighted_fuse(
            dense_res,
            sparse_res,
            splade_res,
            cfg["dense_weight"],
            cfg["sparse_weight"],
            cfg["splade_weight"],
        )

        # deduplicate by db_id
        doclevel = dedup_avg_by_doc(
            fused, client=manager.client, col_name=col, top_k=top_k
        )
        for d in doclevel:
            d["collection"] = col
        merged.extend(doclevel)

    merge_done = time.perf_counter()
    merged.sort(key=lambda x: x["avg_score"], reverse=True)
    merged = merged[:top_k]
    logger.debug(
        f"[Pipeline] merged unique docs={len(merged)} (search+fuse {merge_done - t0:.3f}s)"
    )

    # 2) optional cross-encoder rerank
    if not cfg.get("use_reranker", True):
        return merged

    if not merged:
        return merged

    candidates: List[Dict[str, Any]] = []
    id2meta: Dict[Any, Dict[str, Any]] = {}

    for d in merged:
        db_id = d.get("db_id") or d.get("id") or d.get("parent_id")
        col = d["collection"]
        if not db_id:
            continue

        p = None
        try:
            fetched = manager.client.retrieve(
                collection_name=col, ids=[db_id], with_payload=True
            )
            if fetched:
                p = fetched[0]
            else:
                hits, _ = manager.client.scroll(
                    collection_name=col,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="parent_id", match=MatchValue(value=db_id))]
                    ),
                    limit=1,
                    with_payload=True,
                )
                if hits:
                    p = hits[0]

            if not p:
                continue

            payload = p.payload or {}
            text = payload.get("contents") or payload.get("content") or payload.get("text", "")
            title = payload.get("title") or d.get("title") or "(no title)"

            if not text.strip():
                continue

            candidates.append({"id": db_id, "text": text, "title": title})
            id2meta[db_id] = {
                "title": title,
                "collection": col,
                "avg_score": d.get("avg_score", 0.0),
            }

        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[Pipeline] payload fetch failed for {db_id} in {col}: {exc}")
            continue

    if not candidates:
        logger.warning("[Pipeline] No candidates for rerank; returning fused results")
        return merged

    try:
        reranked, timing = rerank_service(
            query=query_text,
            docs=candidates,
            model_name=cfg.get("cross_encoder_model", "Dongjin-kr/ko-reranker"),
            top_k=top_k,
            device="cpu",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Pipeline] reranker failed, returning fused results: {exc}")
        return merged

    final_after_ce: List[Dict[str, Any]] = []
    for r in reranked:
        meta = id2meta.get(r["id"], {})
        final_after_ce.append(
            {
                "db_id": r["id"],
                "title": meta.get("title"),
                "score": r.get("score", 0.0),
                "collection": meta.get("collection", manager.default_collection),
                "avg_score": meta.get("avg_score", 0.0),
            }
        )

    final_after_ce.sort(key=lambda x: x["score"], reverse=True)
    logger.debug(
        f"[Pipeline] rerank done load={timing.get('load_s',0):.3f}s rerank={timing.get('rerank_s',0):.3f}s"
    )
    return final_after_ce[:top_k]
