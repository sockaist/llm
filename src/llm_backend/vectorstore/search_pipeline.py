"""Hybrid search pipeline orchestration for VectorDBManager.

Keeps the previous behavior (dense + BM25 + SPLADE → fusion → dedup → optional
cross-encoder rerank) but separates the orchestration from the manager class
for readability and testability.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from qdrant_client import models

from llm_backend.utils.logger import logger
from llm_backend.vectorstore.rerank_engine import rerank as rerank_service
from llm_backend.vectorstore.fusion_engine import (
    deduplicate_results as dedup_avg_by_doc,
    weighted_fuse,
    reciprocal_rank_fusion,
    extract_temporal_intent,
    apply_temporal_ranking,
)
from llm_backend.vectorstore.vector_db_helper import query_unique_docs as q_unique


def _augment_parent_context(manager, collections, results):
    """Phase 7 Helper: Attaches full parent text to each result item."""
    if not results:
        return results

    db_ids = list(set(r["db_id"] for r in results if "db_id" in r))
    if not db_ids:
        return results

    parent_map = {}
    for col in collections:
        try:
            parents, _ = manager.client.scroll(
                collection_name=col,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="db_id", match=models.MatchAny(any=db_ids)
                        ),
                        models.FieldCondition(
                            key="is_parent", match=models.MatchValue(value=True)
                        ),
                    ]
                ),
                limit=len(db_ids),
                with_payload=True,
            )
            for p in parents:
                parent_map[p.payload["db_id"]] = p.payload.get("full_text")
        except Exception as e:
            logger.warning(f"[Search] Parent fetch error in {col}: {e}")

    for res in results:
        if "db_id" in res:
            res["parent_context"] = parent_map.get(res["db_id"])

    return results


def build_access_filter(
    user_context: Optional[Dict[str, Any]],
) -> Optional[models.Filter]:
    """
    Phase 12: Build Qdrant Filter for Multi-Tenancy / RBAC.

    Logic:
    1. If no user (Guest) -> Public Content (Level 1)
    2. If User -> Public (up to Level 2) + Own Private Data
    3. If Admin -> All Data
    """
    if not user_context:
        # Defaults to Guest
        user_context = {"user": {"role": "guest", "id": "anonymous"}}

    user_info = user_context.get("user")
    if user_info and isinstance(user_info, dict):
        role = user_info.get("role", "guest")
        user_id = user_info.get("id", "anonymous")
    else:
        role = user_context.get("role", "guest")
        user_id = user_context.get("user_id") or user_context.get("id", "anonymous")

    if role == "admin":
        # Admin: Access ALL Public data, but NOT private tenant data
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant_id", match=models.MatchValue(value="public")
                )
            ]
        )

    # Guest / Viewer constraints
    # Public condition: tenant_id="public" AND access_level <= 1 (Guest) or 2 (User)
    public_level_limit = 2 if role in ["user", "viewer", "editor"] else 1

    public_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="tenant_id", match=models.MatchValue(value="public")
            ),
            models.FieldCondition(
                key="access_level", range=models.Range(lte=public_level_limit)
            ),
        ]
    )

    if role == "guest" or not user_id:
        return public_filter

    # Authenticated User: Public OR Own Data
    return models.Filter(
        should=[
            public_filter,
            models.FieldCondition(
                key="tenant_id", match=models.MatchValue(value=user_id)
            ),
        ]
    )


def run_query_pipeline(
    manager,
    query_text: str,
    top_k: int,
    collections: List[str],
    cfg: Dict[str, Any],
    user_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Execute the hybrid search pipeline using the provided manager.

    Args:
        manager: VectorDBManager instance
        query_text: user query
        top_k: result limit
        collections: list of collection names
        cfg: pipeline_config dict on the manager
    """

    # Phase 12: Build Access Filter
    if not user_context:
        user_context = {"role": "guest", "user_id": "anonymous"}
    access_filter = build_access_filter(user_context)

    merged: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    temporal_cfg = extract_temporal_intent(query_text)
    use_recency = cfg.get("use_recency", temporal_cfg["has_recent_intent"])

    # Increase search depth if we want to rerank by time or filter by year
    expansion = cfg.get("recency_expansion", 3)
    if temporal_cfg["explicit_year"]:
        expansion = max(expansion, 5)  # More candidates if we are filtering
    search_k = top_k * expansion

    # --- Phase 7: Semantic Cache Lookup ---
    from llm_backend.server.vector_server.core.semantic_cache import SemanticCache

    dense_vec = manager.dense_model.encode(
        query_text, show_progress_bar=False
    )  # We need this for cache check
    SemanticCache.init_cache(manager.client, vector_size=1024)
    semantic_hit = SemanticCache.get(
        manager.client, dense_vec, query_text, user_context=user_context
    )
    if semantic_hit:
        return semantic_hit

    # --- Phase 3: Cache Lookup (Exact) ---
    from llm_backend.server.vector_server.core.cache_manager import (
        get_cache,
        make_query_cache_key,
        CacheManager,
    )

    # Cache key now includes search_k, use_recency, explicit filters, AND USER CONTEXT
    u_info = user_context.get("user")
    if u_info and isinstance(u_info, dict):
        uid = u_info.get("id", "anonymous")
        urole = u_info.get("role", "guest")
    else:
        uid = user_context.get("user_id") or user_context.get("id", "anonymous")
        urole = user_context.get("role", "guest")
    user_key_suffix = f"|u:{uid}|r:{urole}"
    # Append suffix to query text for unique key generation
    effective_query_key_text = query_text + user_key_suffix

    # Extra meta for cache set? We just store results.

    cache_key = make_query_cache_key(effective_query_key_text, collections, top_k)
    cached_results = get_cache().get(cache_key)
    if cached_results:
        logger.info(
            f"[Pipeline] Cache Hit! Returning pre-computed results for '{query_text[:20]}...'"
        )
        results = _augment_parent_context(manager, collections, cached_results)

        # Update Semantic Cache
        if not semantic_hit:
            SemanticCache.set(
                manager.client,
                dense_vec,
                results,
                query_text,
                user_context=user_context,
            )

        return results

    # --- Phase 2: Query Reformulation ---
    from llm_backend.server.vector_server.core.query_reformulation import (
        reformulate_query,
    )

    search_query = reformulate_query(query_text)

    # --- Phase 2: Adaptive Fusion ---
    from llm_backend.vectorstore.adaptive_fusion import analyze_query_type

    analyze_query_type(query_text)

    # --- Phase 5 & 6: AutoRAG-HP (Heuristic or Bandit) ---
    if cfg.get("use_bandit", True):
        from .bandit_tuner import BanditHPTuner

        # Persistence would usually be in a DB, here we mock it per-request or use a singleton
        tuner = BanditHPTuner(epsilon=cfg.get("epsilon", 0.1))
        hp = tuner.get_hp(query_text)
        logger.info(f"[AutoRAG-HP] Using Bandit Strategy: {hp['_strategy_used']}")
    else:
        from .hp_tuner import get_optimized_hp

        hp = get_optimized_hp(query_text, cfg)
        hp["_strategy_used"] = "heuristic_static"

    w_dense = hp["dense_weight"]
    w_sparse = hp["sparse_weight"]
    w_splade = hp["splade_weight"]
    w_title = hp["title_weight"]
    search_k = hp["search_k"]

    # Phase 19: Manual Alpha Override (Score = Dense*Alpha + Sparse*(1-Alpha))
    # If alpha is provided, we switch to Weighted Sum Fusion for exact control.
    if "alpha" in cfg and cfg["alpha"] is not None:
        alpha = float(cfg["alpha"])
        logger.info(f"[Pipeline] Manual Alpha Override: {alpha}")
        w_dense = alpha
        w_sparse = 1.0 - alpha
        w_splade = 0.0  # Disable splade/title noise if manual alpha strictly requested? Or scale them?
        w_title = 0.0
        # Force Score Fusion to match the formula exactly
        cfg["use_rrf"] = False
        hp["_strategy_used"] = "manual_override"

    # --- Phase 7: Universal Metadata Routing ---
    from .metadata_router import MetadataRouter

    query_filters = MetadataRouter.extract_filters(query_text)

    # --- Phase 7: Graph-Lite Entity Extraction ---
    from .entity_booster import EntityBooster

    query_entities = EntityBooster.extract_entities(query_text)

    # --- Pre-encode Vectors ---
    # Phase 11: Instruction Tuning Support
    final_query = search_query
    # Check if we are using the fine-tuned model (heuristic based on path/config)
    # Ideally, we should check checks if 'csweb.research' is in target_collections, but for now applying globally
    # for consistent space.
    if "bge-m3-finetuned" in str(manager.dense_model):  # Weak check, but practical
        final_query = "Instruct: Find academic profile " + search_query
    elif (
        "finetuned" in str(manager.dense_model) or True
    ):  # Force instruction for now as we are using the fine-tuned model path
        # Since we updated config.py to point to fine-tuned model, we should use the instruction.
        # The fine-tuned model path is "./bge-m3-finetuned-academic"
        final_query = "Instruct: Find academic profile " + search_query

    dense_vec = (
        manager.dense_model.encode(final_query, show_progress_bar=False)
        if cfg["use_dense"]
        else None
    )
    title_vec = dense_vec  # Phase 5: Simple reuse of dense embedding if not specialized

    sparse_sv = None
    if cfg["use_sparse"]:
        from llm_backend.vectorstore.sparse_engine import bm25_encode
        from qdrant_client.models import SparseVector

        b_vec = bm25_encode(search_query)
        sparse_sv = SparseVector(
            indices=[int(k) for k in b_vec.keys()],
            values=[float(v) for v in b_vec.values()],
        )

    splade_sv = None
    if cfg["use_splade"]:
        from llm_backend.vectorstore.sparse_engine import splade_encode
        from qdrant_client.models import SparseVector

        s_vec = splade_encode(search_query)
        splade_sv = SparseVector(
            indices=[int(k) for k in s_vec.keys()],
            values=[float(v) for v in s_vec.values()],
        )

    # 1. Parallel search and fusion across collections
    from concurrent.futures import ThreadPoolExecutor

    # Phase 12: Merge Access Filter with Metadata Routing Filters
    def merge_filters(meta_filter, sec_filter):
        if not meta_filter and not sec_filter:
            return None
        if not meta_filter:
            return sec_filter
        if not sec_filter:
            return meta_filter

        # Combine with MUST
        return models.Filter(
            must=[meta_filter, sec_filter]  # Nested filter support in Qdrant
        )

    final_filter = merge_filters(query_filters, access_filter)

    def process_collection(col, q_unique=q_unique):
        try:
            d_res, s_res, sp_res, t_res = [], [], [], []
            if dense_vec is not None:
                d_res = q_unique(
                    manager.client,
                    col,
                    dense_vec,
                    "dense",
                    search_k,
                    query_filter=final_filter,
                )
                t_res = q_unique(
                    manager.client,
                    col,
                    title_vec,
                    "title",
                    search_k,
                    query_filter=final_filter,
                )
            if sparse_sv is not None:
                s_res = q_unique(
                    manager.client,
                    col,
                    sparse_sv,
                    "sparse",
                    search_k,
                    query_filter=final_filter,
                )
            if splade_sv is not None:
                sp_res = q_unique(
                    manager.client,
                    col,
                    splade_sv,
                    "splade",
                    search_k,
                    query_filter=final_filter,
                )

            if cfg.get("use_rrf", True):
                # RRF Fusion (Rank-based)
                # Default k=60 is standard for RRF
                fused = reciprocal_rank_fusion(
                    d_res,
                    s_res,
                    sp_res,
                    k=cfg.get("rrf_k", 60),
                    title_results=t_res,
                    weights={
                        "dense": w_dense,
                        "sparse": w_sparse,
                        "splade": w_splade,
                        "title": w_title,
                    },
                )
            else:
                # Legacy Score-based Fusion
                fused = weighted_fuse(
                    d_res,
                    s_res,
                    sp_res,
                    w_dense,
                    w_sparse,
                    w_splade,
                    title_results=t_res,
                    title_weight=w_title,
                )

            # Debug RRF inputs
            if cfg.get("use_rrf", False):
                logger.info(
                    f"[RRF Debug] {col}: dense={len(d_res)} sparse={len(s_res)} splade={len(sp_res)} title={len(t_res)}"
                )

            doclevel = dedup_avg_by_doc(
                fused, client=manager.client, col_name=col, top_k=search_k
            )
            for d in doclevel:
                d["collection"] = col
            return doclevel
        except Exception as e:
            logger.error(f"[Pipeline] Error processing collection '{col}': {e}")
            return []

    with ThreadPoolExecutor(max_workers=min(len(collections), 16)) as executor:
        results = list(executor.map(process_collection, collections))

    for doclevel in results:
        for d in doclevel:
            d["id"] = d.get("db_id")
        merged.extend(doclevel)

    # --- Phase 10: Filter Fallback (Fix Zero-Result Bug) ---
    if not merged and query_filters:
        logger.warning(
            f"[Pipeline] 0 results with filters {query_filters}. Triggering Fallback (No Filter)."
        )

        # Retry without filters
        def process_collection_nofilter(col):
            d_res, s_res, sp_res, t_res = [], [], [], []
            if dense_vec is not None:
                d_res = q_unique(
                    manager.client,
                    col,
                    dense_vec,
                    "dense",
                    search_k,
                    query_filter=access_filter,
                )
                t_res = q_unique(
                    manager.client,
                    col,
                    title_vec,
                    "title",
                    search_k,
                    query_filter=access_filter,
                )
            if sparse_sv is not None:
                s_res = q_unique(
                    manager.client,
                    col,
                    sparse_sv,
                    "sparse",
                    search_k,
                    query_filter=access_filter,
                )
            if splade_sv is not None:
                sp_res = q_unique(
                    manager.client,
                    col,
                    splade_sv,
                    "splade",
                    search_k,
                    query_filter=access_filter,
                )

            if cfg.get("use_rrf", True):
                fused = reciprocal_rank_fusion(
                    d_res,
                    s_res,
                    sp_res,
                    k=cfg.get("rrf_k", 60),
                    title_results=t_res,
                    weights={
                        "dense": w_dense,
                        "sparse": w_sparse,
                        "splade": w_splade,
                        "title": w_title,
                    },
                )
            else:
                fused = weighted_fuse(
                    d_res,
                    s_res,
                    sp_res,
                    w_dense,
                    w_sparse,
                    w_splade,
                    title_results=t_res,
                    title_weight=w_title,
                )

            doclevel = dedup_avg_by_doc(
                fused, client=manager.client, col_name=col, top_k=search_k
            )
            for d in doclevel:
                d["collection"] = col
            return doclevel

        with ThreadPoolExecutor(max_workers=min(len(collections), 16)) as executor:
            fallback_results = list(
                executor.map(process_collection_nofilter, collections)
            )

        for doclevel in fallback_results:
            for d in doclevel:
                d["id"] = d.get("db_id")
                # Mark as fallback result
                d["_fallback_triggered"] = True
            merged.extend(doclevel)

        logger.info(f"[Fallback] Recovered {len(merged)} docs without filters.")

    time.perf_counter()
    merged.sort(key=lambda x: x["avg_score"], reverse=True)

    # --- Phase 4: Python-side Hard Filtering ---
    if temporal_cfg["explicit_year"]:
        year_str = str(temporal_cfg["explicit_year"])
        filtered = []
        for d in merged:
            date_val = d.get("payload", {}).get("date")
            if date_val and year_str in str(date_val):
                filtered.append(d)
        if filtered:
            merged = filtered
            logger.info(
                f"[Temporal] Hard-filtered {len(merged)} docs for year {year_str}"
            )

    # --- Phase 4: Temporal Ranking ---
    if use_recency:
        alpha = cfg.get("temp_alpha", temporal_cfg["alpha"])
        half_life = cfg.get("half_life_days", temporal_cfg["half_life"])
        merged = apply_temporal_ranking(
            merged, alpha=alpha, half_life_days=half_life, top_k=search_k
        )

    merged = merged[:top_k]
    logger.debug(
        f"[Pipeline] merged unique docs={len(merged)} (search+fuse+temp {time.perf_counter() - t0:.3f}s)"
    )

    # 2) optional cross-encoder rerank
    if not cfg.get("use_reranker", True):
        results = _augment_parent_context(manager, collections, merged)
        results = _decrypt_results(results, user_context)
        get_cache().set(cache_key, results, ttl=3600)
        if not semantic_hit:
            SemanticCache.set(
                manager.client,
                dense_vec,
                results,
                query_text,
                user_context=user_context,
            )
        return results

    if not merged:
        return []

    # --- Phase 3: Confidence Triage ---
    if not use_recency and CacheManager.should_skip_rerank(
        merged, threshold=cfg.get("triage_threshold", 0.98)
    ):
        # If confidence is high, just return fused results (with 'score' aliased)
        for d in merged:
            d["score"] = d.get("avg_score", 0.0)
        results = _augment_parent_context(manager, collections, merged)
        results = _decrypt_results(results, user_context)
        get_cache().set(cache_key, results, ttl=3600)
        if not semantic_hit:
            SemanticCache.set(
                manager.client,
                dense_vec,
                results,
                query_text,
                user_context=user_context,
            )
        return results

    # --- Batch Payload Retrieval (No longer needed since payloads are in 'merged') ---
    candidates: List[Dict[str, Any]] = []
    id2meta: Dict[Any, Dict[str, Any]] = {}

    for d in merged:
        db_id = d.get("db_id")
        text = d.get("text")
        title = d.get("title") or "(no title)"
        col = d.get("collection")

        if not db_id or not text or not text.strip():
            continue

        candidates.append({"id": db_id, "text": text, "title": title})
        id2meta[db_id] = {
            "title": title,
            "collection": col,
            "avg_score": d.get("avg_score", 0.0),
            "payload": d.get("payload", {}),
            "cosine_similarity": d.get("cosine_similarity"),
            "recency_score": d.get("recency_score"),
        }

    if not candidates:
        logger.warning("[Pipeline] No candidates for rerank; returning merged results")
        results = _augment_parent_context(manager, collections, merged)
        results = _decrypt_results(results, user_context)
        if not semantic_hit:
            SemanticCache.set(
                manager.client,
                dense_vec,
                results,
                query_text,
                user_context=user_context,
            )
        return results

    try:
        reranked, timing = rerank_service(
            query=query_text,
            docs=candidates,
            model_name=cfg.get(
                "cross_encoder_model", "BAAI/bge-reranker-v2-m3"
            ),  # Phase 10: Upgrade
            top_k=top_k,
            device="cpu",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Pipeline] reranker failed: {exc}")
        results = _augment_parent_context(manager, collections, merged)
        results = _decrypt_results(results, user_context)
        return results

    if not reranked:
        logger.warning("[Pipeline] Reranker returned no results.")
        results = _augment_parent_context(manager, collections, merged)
        results = _decrypt_results(results, user_context)
        return results

    final_results: List[Dict[str, Any]] = []
    alpha = cfg.get("temp_alpha", temporal_cfg["alpha"])

    # Normalize reranker scores for combination (0-1 range)
    r_scores = [r.get("score", 0.0) for r in reranked]
    r_min, r_max = min(r_scores), max(r_scores)

    for r in reranked:
        meta = id2meta.get(r["id"], {})
        r_score_raw = r.get("score", 0.0)
        # Avoid division by zero
        r_score_norm = (
            (r_score_raw - r_min) / (r_max - r_min) if r_max != r_min else 0.5
        )

        rec_score = meta.get("recency_score", 0.3)

        # If recency is active, fuse semantic score (reranker) with temporal score
        if use_recency:
            final_score = alpha * r_score_norm + (1 - alpha) * rec_score
        else:
            final_score = r_score_raw

        final_results.append(
            {
                "id": r["id"],
                "db_id": r["id"],
                "title": meta.get("title"),
                "text": r.get("text"),
                "score": float(final_score),
                "rerank_score": float(r_score_raw),
                "avg_score": meta.get("avg_score", 0.0),
                "collection": meta.get("collection", manager.default_collection),
                "payload": meta.get("payload", {}),
                "cosine_similarity": meta.get("cosine_similarity"),
                "recency_score": rec_score,
                "_strategy_used": hp.get("_strategy_used", "unknown"),
            }
        )

    final_results.sort(key=lambda x: x["score"], reverse=True)
    results = final_results[:top_k]

    # --- Phase 7: Parent Context Augmentation ---
    results = _augment_parent_context(manager, collections, results)

    # Decryption Step (Phase 13)
    results = _decrypt_results(results, user_context)

    # --- Phase 7: Graph-Lite Entity Boosting ---
    results = EntityBooster.apply_boost(results, query_entities)

    # --- Phase 3: Cache Save ---
    get_cache().set(cache_key, results, ttl=3600)

    # --- Phase 7: Semantic Cache Set ---
    if not semantic_hit:
        SemanticCache.set(
            manager.client, dense_vec, results, query_text, user_context=user_context
        )

    logger.debug(
        f"[Pipeline] rerank done load={timing.get('load_s', 0):.3f}s rerank={timing.get('rerank_s', 0):.3f}s"
    )
    return results


def _decrypt_results(
    results: List[Dict[str, Any]], user_context: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Decrypt content if the user owns the document."""
    if not results or not user_context:
        return results

    user_info = user_context.get("user")
    if user_info and isinstance(user_info, dict):
        user_id = user_info.get("id")
    else:
        user_id = user_context.get("user_id") or user_context.get("id")

    if not user_id or user_id == "anonymous":
        return results

    try:
        from llm_backend.server.vector_server.core.security.encryption_manager import (
            EncryptionManager,
        )

        encryptor = EncryptionManager.get_instance()
    except ImportError:
        logger.warning("[Decryption] EncryptionManager not found.")
        return results

    for r in results:
        payload = r.get("metadata", {}) or r.get("payload", {})

        # Check if encrypted (flag in payload)
        if payload.get("content_encrypted"):
            # Check ownership
            if payload.get("tenant_id") == user_id:
                try:
                    # Decrypt 'content' in payload
                    encrypted_text = payload.get("content", "")
                    if encrypted_text:
                        decrypted_text = encryptor.decrypt_text(user_id, encrypted_text)

                        # Update payload and main text field
                        payload["content"] = decrypted_text
                        payload["content_encrypted"] = (
                            False  # Mark as decrypted for this view
                        )
                        r["text"] = decrypted_text

                        # Apply updates to references
                        if "payload" in r:
                            r["payload"] = payload
                        if "metadata" in r:
                            r["metadata"] = payload
                except Exception as e:
                    logger.error(f"[Decryption] Failed for doc {r.get('id')}: {e}")
                    r["text"] = "[Decryption Failed]"
                    payload["content"] = "[Decryption Failed]"

    return results
