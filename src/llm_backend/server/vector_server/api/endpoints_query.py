# llm_backend/server/vector_server/api/endpoints_query.py
# -*- coding: utf-8 -*-
import os
import asyncio
from fastapi import APIRouter, HTTPException, Request, Depends
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.server.vector_server.models.request_models import QueryRequest, KeywordSearchRequest
from llm_backend.server.vector_server.models.response_models import QueryResponse
from llm_backend.server.vector_server.core.cache_manager import (
    get_cache, make_query_cache_key
)
from llm_backend.server.vector_server.core.auth import get_user_context
# Security Imports
from llm_backend.server.vector_server.core.security.access_control import Action
from llm_backend.server.vector_server.core.security.defense import defense_system
from llm_backend.server.vector_server.core.security.audit_logger import audit_logger
from llm_backend.server.vector_server.core.security.data_filter import SensitiveDataFilter
from llm_backend.utils.logger import logger

# ... (Previous imports and code) ...

@router.post("/hybrid", response_model=QueryResponse)
async def query_hybrid(req: QueryRequest, request: Request, user_context: dict = Depends(get_user_context)):
    """
    기존 하이브리드 검색 (Dense + Sparse + Rerank)
    """
    try:
        # 1. Defense: Rate Limit & Injection Check
        access_manager = request.state.access_manager
        
        # User ID for Rate Limit Check (already done globally in middleware, but Injection check is here)
        user_id = user_context.get("user", {}).get("id")
        
        # Injection Check
        is_allowed, reason = defense_system.validate_request(user_id, query=req.query_text)
        if not is_allowed:
             await audit_logger.log_event("injection_detected", {
                 "user": user_id, 
                 "query": req.query_text, 
                 "reason": reason
             })
             raise HTTPException(status_code=400, detail=f"Security Error: {reason}")

        # 2. Access Control Check (Search Permission)
        allowed, reason = access_manager.check_permission(user_context, {}, Action.SEARCH)
        if not allowed:
             raise HTTPException(status_code=403, detail=f"Access Denied: {reason}")

        # 3. Validation & API6 Quota Check
        if not (1 <= req.top_k <= MAX_TOP_K):
            raise HTTPException(status_code=400, detail=f"Invalid top_k (1~{MAX_TOP_K} allowed)")

        # API6: Quota Check
        user_role = user_context.get("user", {}).get("role")
        quota_ok, reason = defense_system.validate_quota(user_id, user_role, count=req.top_k)
        if not quota_ok:
             await audit_logger.log_event("quota_exceeded_search", {"user": user_id, "attempt": req.top_k, "reason": reason})
             raise HTTPException(status_code=429, detail=f"Quota Exceeded: {reason}")

        logger.info(f"[API:/query/hybrid] '{req.query_text}' (top_k={req.top_k})")

        # 4. Cache Check
        cache = get_cache()
        key = make_query_cache_key(req.query_text, req.collections, req.top_k)
        hit = cache.get(key)
        if hit:
            # API3: Must filter cache hits too because they contain raw payload
            scrubbed_hit = SensitiveDataFilter.filter_search_results(hit, user_context)
            await audit_logger.log_event("query_cache_hit", {"user": user_context.get("user", {}).get("id")})
            return QueryResponse(status="success", results=scrubbed_hit)

        # 5. Search
        with acquire_manager() as mgr:
            # ... (Previous logic to determine target_cols) ...
            
            # Filter target cols based on Access Control (ABAC filtering)
            allowed_cols = []
            for col in target_cols:
                can_read, _ = access_manager.check_permission(user_context, {"collection": col}, Action.READ)
                if can_read:
                    allowed_cols.append(col)
            
            if not allowed_cols:
                 return QueryResponse(status="success", results=[])

            # Phase 19: Tuning Overrides
            overrides = {}
            if req.alpha is not None:
                overrides["alpha"] = req.alpha
            if req.tuning_mode:
                overrides["tuning_mode"] = req.tuning_mode

            results = await asyncio.to_thread(
                mgr.query,
                req.query_text,
                req.top_k,
                allowed_cols,
                user_context=user_context,
                pipeline_overrides=overrides
            )

        # 6. Cache Save (Save RAW results to cache for reuse by different roles, scrub on retrieve)
        # Note: If we save scrubbed, admins might get scrubbed data. Better to save full and scrub on exit.
        cache.set(key, results, ttl=600)

        # 7. Audit Log (Async Tier 2)
        await audit_logger.log_event("vector_search", {
            "user": user_context.get("user", {}).get("id"),
            "query_hash": hash(req.query_text), 
            "collections": allowed_cols,
            "result_count": len(results)
        })

        # API3: Sensitive Data Filtering
        scrubbed_results = SensitiveDataFilter.filter_search_results(results, user_context)

        return QueryResponse(status="success", results=scrubbed_results)

    except HTTPException:
        raise
    except Exception as e:
        # ... (Error handling) ...
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keyword", response_model=QueryResponse)
async def query_keyword(req: KeywordSearchRequest, request: Request, user_context: dict = Depends(get_user_context)):
    """
    BM25 키워드 검색 (Rerank 없음, 고속)
    """
    try:
        if not (1 <= req.top_k <= MAX_TOP_K):
            raise HTTPException(status_code=400, detail=f"Invalid top_k (1~{MAX_TOP_K} allowed)")
            
        # API6: Business Flow Protection (Quota)
        user_role = user_context.get("user", {}).get("role")
        user_id = user_context.get("user", {}).get("id")
        
        quota_ok, reason = defense_system.validate_quota(user_id, user_role, count=req.top_k)
        if not quota_ok:
             await audit_logger.log_event("quota_exceeded_keyword", {"user": user_id, "attempt": req.top_k, "reason": reason})
             raise HTTPException(status_code=429, detail=f"Quota Exceeded: {reason}")

        logger.info(f"[API:/query/keyword] '{req.query}' (top_k={req.top_k})")

        with acquire_manager() as mgr:
            results = await asyncio.to_thread(mgr.search_keyword, req.query, top_k=req.top_k, user_context=user_context)
            
        await audit_logger.log_event("keyword_search", {
            "user": user_context.get("user", {}).get("id"),
            "query_hash": hash(req.query),
            "result_count": len(results)
        })
        
        # API3: Sensitive Data Filtering
        scrubbed_results = SensitiveDataFilter.filter_search_results(results, user_context)
            
        return QueryResponse(status="success", results=scrubbed_results)

    except HTTPException:
        raise
    except Exception as e:
        # ... (Error handling) ...
        raise HTTPException(status_code=500, detail=str(e))