# llm_backend/server/vector_server/api/endpoints_query.py
# -*- coding: utf-8 -*-
import os
import asyncio
from fastapi import APIRouter, HTTPException
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.server.vector_server.models.request_models import QueryRequest, KeywordSearchRequest
from llm_backend.server.vector_server.models.response_models import QueryResponse
from llm_backend.server.vector_server.core.cache_manager import (
    get_cache, make_query_cache_key
)
from llm_backend.utils.logger import logger

router = APIRouter(prefix="/query", tags=["Query"])

# 환경변수에서 상한을 읽어 한 곳에서만 관리
MAX_TOP_K = int(os.getenv("MAX_TOP_K", "50"))

@router.post("/hybrid", response_model=QueryResponse)
async def query_hybrid(req: QueryRequest):
    """
    기존 하이브리드 검색 (Dense + Sparse + Rerank)
    """
    try:
        # 1) 입력 유효성 검사: top_k 범위
        if not (1 <= req.top_k <= MAX_TOP_K):
            raise HTTPException(status_code=400, detail=f"Invalid top_k (1~{MAX_TOP_K} allowed)")

        logger.info(f"[API:/query/hybrid] '{req.query_text}' (top_k={req.top_k})")

        # 2) 캐시 조회
        cache = get_cache()
        key = make_query_cache_key(req.query_text, req.collections, req.top_k)
        hit = cache.get(key)
        if hit:
            return QueryResponse(status="success", results=hit)

        # 3) 실제 쿼리
        # 3) 실제 쿼리
        with acquire_manager() as mgr:
            # 컬렉션 지정 없으면 전체 대상 검색
            target_cols = req.collections
            if not target_cols:
                # Qdrant에서 전체 컬렉션 목록 조회
                try:
                    resp = mgr.client.get_collections()
                    target_cols = [c.name for c in resp.collections]
                    if not target_cols:
                        target_cols = [mgr.default_collection]
                except Exception as e:
                    logger.error(f"[Query] Failed to fetch all collections: {e}")
                    target_cols = [mgr.default_collection]

            results = await asyncio.to_thread(
                mgr.query,
                req.query_text,
                req.top_k,
                target_cols,
            )

        # 4) 캐시 저장 (10분)
        cache.set(key, results, ttl=600)

        return QueryResponse(status="success", results=results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API:/query/hybrid] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keyword", response_model=QueryResponse)
async def query_keyword(req: KeywordSearchRequest):
    """
    BM25 키워드 검색 (Rerank 없음, 고속)
    """
    try:
        if not (1 <= req.top_k <= MAX_TOP_K):
            raise HTTPException(status_code=400, detail=f"Invalid top_k (1~{MAX_TOP_K} allowed)")

        logger.info(f"[API:/query/keyword] '{req.query}' (top_k={req.top_k})")

        with acquire_manager() as mgr:
            results = await asyncio.to_thread(mgr.search_keyword, req.query, top_k=req.top_k)
            
        return QueryResponse(status="success", results=results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API:/query/keyword] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 하위 호환성 (기존 /query 루트 경로)
@router.post("", response_model=QueryResponse, deprecated=True)
async def query_documents_legacy(req: QueryRequest):
    return await query_hybrid(req)