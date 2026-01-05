# llm_backend/server/vector_server/api/endpoints_admin.py
# -*- coding: utf-8 -*-
import os
import time
import re
import hmac
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from llm_backend.server.vector_server.core.auth import verify_api_key
from llm_backend.server.vector_server.manager.snapshot_manager import (
    create_snapshot,
    list_snapshots,
    delete_snapshot,
    restore_snapshot,
)
from llm_backend.server.vector_server.core.cache_manager import (
    get_cache,
    bump_collection_epoch,
)
from llm_backend.server.vector_server.core.queue_manager import (
    list_jobs,
    enqueue_job,
    is_job_active,
    last_completed_at,
)
from llm_backend.server.vector_server.models.request_models import (
    SnapshotPathRequest,
    SnapshotDeleteRequest,
    BM25RetrainRequest,
    CreateCollectionRequest,
    DeleteCollectionRequest,
)
from llm_backend.server.vector_server.models.response_models import (
    SnapshotResponse,
    BatchResponse,
    CollectionListResponse,
)
from llm_backend.utils.logger import logger
from llm_backend.vectorstore.config import DEFAULT_COLLECTION_NAME

router = APIRouter(
    prefix="/admin", tags=["Admin"]
)

# -----------------------------
# Snapshot
# -----------------------------

# ----- (선택) 비밀키 해시 준비: 평문 비교 대신 안전 비교 -----
_ADMIN_SECRET_RAW = os.getenv("ADMIN_SECRET")
_ADMIN_SECRET_HASH = (
    hashlib.sha256(_ADMIN_SECRET_RAW.encode()).hexdigest()
    if _ADMIN_SECRET_RAW
    else None
)


def _check_admin_secret(x_admin_secret: Optional[str]):
    # 환경변수 설정 없으면 개발 모드로 간주하고 통과
    if not _ADMIN_SECRET_HASH:
        return

    if not x_admin_secret:
        raise HTTPException(status_code=403, detail="Admin secret required")

    given = hashlib.sha256(x_admin_secret.encode()).hexdigest()
    if not hmac.compare_digest(given, _ADMIN_SECRET_HASH):
        raise HTTPException(status_code=403, detail="Admin secret invalid")


# 컬렉션명 간단 검증(영숫자/._- 최대 64자)
_NAME_RX = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _validate_collection_name(name: str):
    if not _NAME_RX.match(name):
        raise HTTPException(status_code=400, detail="Invalid collection name")


# -----------------------------
# 컬렉션 목록 조회
# -----------------------------
@router.get("/collections/list", response_model=CollectionListResponse)
async def list_collections_endpoint(x_admin_secret: Optional[str] = Header(None)):
    try:
        _check_admin_secret(x_admin_secret)
        from llm_backend.server.vector_server.core.resource_pool import acquire_manager

        with acquire_manager() as mgr:
            info_list = mgr.list_collections_info()

        return CollectionListResponse(
            status="success", collections=info_list, total_count=len(info_list)
        )
    except Exception as e:
        logger.error(f"[Admin:/collections/list] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# 컬렉션 생성 (Body 전용)
# -----------------------------
@router.post("/collections/create", response_model=SnapshotResponse)
async def create_collection_api(
    req: CreateCollectionRequest,
    x_admin_secret: Optional[str] = Header(None),
):
    try:
        _check_admin_secret(x_admin_secret)
        _validate_collection_name(req.name)
        from llm_backend.server.vector_server.core.resource_pool import acquire_manager

        with acquire_manager() as mgr:
            # VectorDBManager에 이미 있으면 그대로 사용, 없으면 예시 구현 참고
            mgr.create_collection(req.name, vector_size=req.vector_size)
        # 새 컬렉션 캐시 충돌 방지: 에폭 1 증가(키 분기)
        bump_collection_epoch(req.name)
        return SnapshotResponse(
            status="success", message=f"Collection '{req.name}' created"
        )
    except Exception as e:
        logger.error(f"[Admin:/collections/create] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# 컬렉션 삭제 (Body 전용)
# -----------------------------
@router.post("/collections/delete", response_model=SnapshotResponse)
async def delete_collection_api(
    req: DeleteCollectionRequest,
    x_admin_secret: Optional[str] = Header(None),
):
    try:
        _check_admin_secret(x_admin_secret)
        _validate_collection_name(req.name)
        from llm_backend.server.vector_server.core.resource_pool import acquire_manager

        with acquire_manager() as mgr:
            mgr.delete_collection(req.name)
        # 캐시 무효화(이 컬렉션 관련 키를 epoch 분기로 ‘끊음’)
        bump_collection_epoch(req.name)
        return SnapshotResponse(
            status="deleted", message=f"Collection '{req.name}' deleted"
        )
    except Exception as e:
        logger.error(f"[Admin:/collections/delete] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# 전체 초기화 (모든 컬렉션 삭제)
# -----------------------------
@router.post("/reset_db", response_model=SnapshotResponse)
async def reset_db_api(x_admin_secret: Optional[str] = Header(None)):
    try:
        _check_admin_secret(x_admin_secret)
        from llm_backend.server.vector_server.core.resource_pool import acquire_manager

        with acquire_manager() as mgr:
            mgr.delete_all_collections()  # 아래 3) 참고: VectorDBManager에 구현 필요
        # 전역 캐시 비우기(안전)
        get_cache().clear()
        return SnapshotResponse(status="success", message="All collections dropped")
    except Exception as e:
        logger.error(f"[Admin:/reset_db] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/create", response_model=SnapshotResponse)
async def create_snapshot_api(
    collection: str = DEFAULT_COLLECTION_NAME,
    comment: Optional[str] = None,
    x_admin_secret: Optional[str] = Header(None),
):
    try:
        _check_admin_secret(x_admin_secret)
        
        # Enqueue Job instead of sync call
        job_payload = {"collection": collection}
        if comment:
            job_payload["comment"] = comment
            
        job_id = enqueue_job("create_snapshot", job_payload)

        # Log Audit Event
        logger.info(
            f"[Audit] Snapshot job enqueued for {collection}. Job ID: {job_id}"
        )

        return SnapshotResponse(
            status="queued",
            path="", # Path is unknown until job finishes
            message=f"Snapshot creation queued. Job ID: {job_id}",
        )
    except Exception as e:
        logger.error(f"[Admin:/snapshot/create] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/list", response_model=SnapshotResponse)
async def list_snapshot_api(x_admin_secret: Optional[str] = Header(None)):
    try:
        _check_admin_secret(x_admin_secret)
        snapshots = list_snapshots()
        return SnapshotResponse(
            status="success", count=len(snapshots), snapshots=snapshots
        )
    except Exception as e:
        logger.error(f"[Admin:/snapshot/list] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Body 전용: 복원
@router.post("/snapshot/restore", response_model=SnapshotResponse)
async def restore_snapshot_api(
    req: SnapshotPathRequest,
    x_admin_secret: Optional[str] = Header(None)
):
    try:
        _check_admin_secret(x_admin_secret)
        restore_snapshot(req.path)
        return SnapshotResponse(status="restored", path=req.path)
    except Exception as e:
        logger.error(f"[Admin:/snapshot/restore] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Body 전용: 삭제 (권장)
@router.post("/snapshot/delete", response_model=SnapshotResponse)
async def delete_snapshot_api(
    req: SnapshotDeleteRequest,
    x_admin_secret: Optional[str] = Header(None)
):
    try:
        _check_admin_secret(x_admin_secret)
        success = delete_snapshot(req.path)
        if not success:
            raise HTTPException(
                status_code=404, detail="Snapshot not found or not allowed"
            )
        return SnapshotResponse(status="deleted", path=req.path)
    except Exception as e:
        logger.error(f"[Admin:/snapshot/delete] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# (선택) 구버전 호환: Query 버전은 문서 비표시 + deprecated
# from fastapi import Query
# @router.delete("/snapshot/delete", response_model=SnapshotResponse, include_in_schema=False)
# async def delete_snapshot_api_legacy(path: str = Query(...)):
#     logger.warning("[Admin] Deprecated /snapshot/delete with querystring used")
#     success = delete_snapshot(path)
#     if not success:
#         raise HTTPException(status_code=404, detail="Snapshot not found or not allowed")
#     return SnapshotResponse(status="deleted", path=path)


# -----------------------------
# Cache
# -----------------------------
@router.post("/cache/clear", response_model=SnapshotResponse)
async def clear_cache_api(x_admin_secret: Optional[str] = Header(None)):
    try:
        _check_admin_secret(x_admin_secret)
        cache = get_cache()
        cache.clear()
        logger.info("[Admin] Cache cleared successfully")
        return SnapshotResponse(status="cleared", message="Cache reset successful")
    except Exception as e:
        logger.error(f"[Admin:/cache/clear] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# BM25 retrain & Jobs
# -----------------------------
@router.post("/bm25/retrain", response_model=BatchResponse)
async def retrain_bm25_api(
    req: BM25RetrainRequest = BM25RetrainRequest(),
    x_admin_secret: Optional[str] = Header(None)
):
    try:
        _check_admin_secret(x_admin_secret)
        # 동일한 중복/쿨다운 정책 적용
        if os.getenv("ALLOW_BM25_BATCH", "1") != "1":
            raise HTTPException(
                status_code=403, detail="BM25 batch trigger is disabled by config"
            )
        if is_job_active("bm25_retrain"):
            return BatchResponse(
                status="skipped", message="A BM25 job is already queued or running"
            )
        job_id = enqueue_job("bm25_retrain", {"base_path": req.base_path})
        return BatchResponse(status="queued", job_id=job_id, type="bm25_retrain")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin:/bm25/retrain] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/jobs/list", response_model=BatchResponse, response_model_exclude_none=True
)
async def list_admin_jobs(
    limit: int = 10,
    x_admin_secret: Optional[str] = Header(None)
):
    try:
        _check_admin_secret(x_admin_secret)
        jobs = list_jobs(limit)
        return BatchResponse(status="success", jobs=jobs.get("jobs", []))
    except Exception as e:
        logger.error(f"[Admin:/jobs/list] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/trigger/bm25", response_model=BatchResponse)
async def trigger_bm25_job(x_admin_secret: Optional[str] = Header(None)):
    """
    BM25 재학습 작업을 백그라운드 큐에 등록합니다.
    """
    try:
        _check_admin_secret(x_admin_secret)
        # 1) 배치 트리거 전역 비활성화 옵션
        if os.getenv("ALLOW_BM25_BATCH", "1") != "1":
            raise HTTPException(
                status_code=403, detail="BM25 batch trigger is disabled by config"
            )

        # 2) 활성 작업 중복 방지
        if is_job_active("bm25_retrain"):
            return BatchResponse(
                status="skipped", message="A BM25 job is already queued or running"
            )

        # 3) 쿨다운(분)
        cooldown_min = int(os.getenv("BM25_COOLDOWN_MIN", "30"))
        ts = last_completed_at("bm25_retrain")
        if ts is not None:
            elapsed_min = int((time.time() - ts) / 60)
            if elapsed_min < cooldown_min:
                return BatchResponse(
                    status="skipped",
                    message=f"Last BM25 retrain finished {elapsed_min}m ago; cooldown={cooldown_min}m",
                )

        # 4) 큐 등록
        job_id = enqueue_job("bm25_retrain", {"base_path": "./data"})
        logger.info(f"[Admin] BM25 retrain job enqueued: {job_id[:8]}")
        return BatchResponse(status="queued", job_id=job_id, type="bm25_retrain")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Admin:/jobs/trigger/bm25] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
