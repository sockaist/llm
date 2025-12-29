# -*- coding: utf-8 -*-
from fastapi import APIRouter
from llm_backend.utils.logger import logger
from llm_backend.server.vector_server.core.resource_pool import (
    get_pool_status, acquire_manager
)
from llm_backend.server.vector_server.core.session_manager import get_session_manager
from llm_backend.server.vector_server.core.cache_manager import get_cache
from llm_backend.server.vector_server.core.queue_manager import list_jobs

router = APIRouter(prefix="/health", tags=["Health & Monitoring"])


# ------------------------------------------------------------
# 기본 헬스체크 (/health)
# ------------------------------------------------------------
@router.get("")
async def health_check():
    """
    FastAPI 서버 동작 여부 확인 (단순 ping).
    """
    logger.info("[Health] Health check endpoint called")
    return {"status": "ok", "message": "Vector server is alive"}


# ------------------------------------------------------------
# 상태 점검 (/health/status)
# ------------------------------------------------------------
@router.get("/status")
async def system_status():
    """
    시스템 내부 구성요소의 현재 상태를 반환합니다.
    - Resource Pool
    - Session Manager
    - Cache
    - Job Queue
    - Qdrant 연결 상태
    """
    try:
        # 각 모듈 상태 수집
        pool_info = get_pool_status()
        session_mgr = get_session_manager()
        cache = get_cache()
        jobs_info = list_jobs(limit=10)

        # 캐시 상태 확인
        cache_backend = getattr(cache, "backend", lambda: "unknown")()
        cache_size = len(getattr(cache, "_cache", {})) if cache_backend == "in-memory" else "N/A"

        # Qdrant ping (간단 연결 테스트)
        qdrant_ok = False
        try:
            with acquire_manager() as m:
                # 호출에 성공하면 연결 OK로 판단
                _ = m.client.get_collections()
                qdrant_ok = True
        except Exception as e:
            logger.warning(f"[Status] Qdrant ping failed: {e}")
            qdrant_ok = False

        status = {
            "server": "running",
            "resource_pool": pool_info,
            "active_sessions": len(session_mgr.list_sessions()),
            "cache": {
                "backend": cache_backend,
                "entries": cache_size,
            },
            "jobs": {
                "total": len(jobs_info.get("jobs", [])),
                "latest": jobs_info.get("jobs", [])[:3],  # 최근 3개만 표시
            },
            "qdrant": {
                "reachable": qdrant_ok
            },
        }

        logger.info("[Status] System status retrieved successfully")
        return status

    except Exception as e:
        logger.error(f"[Status] Failed to collect system status: {e}")
        return {"status": "error", "detail": str(e)}