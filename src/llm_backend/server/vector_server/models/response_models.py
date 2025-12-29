# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# ============================================================
# 공용 응답 모델
# ============================================================
class BaseResponse(BaseModel):
    status: str
    message: Optional[str] = None

# ============================================================
# Query 응답
# ============================================================
class QueryResponse(BaseResponse):
    results: List[Dict[str, Any]]

# ============================================================
# CRUD 응답
# ============================================================
class CRUDResponse(BaseResponse):
    collection: Optional[str] = None
    filename: Optional[str] = None
    db_id: Optional[str] = None

# ============================================================
# Job 객체 (단일 상태 조회 시 사용)
# ============================================================
class JobStatus(BaseModel):
    id: str
    type: str
    status: str
    progress: float
    message: str
    created_at: float
    # Pydantic v1/v2 호환을 위해 extra 무시가 필요하면 아래 주석 해제
    # class Config:
    #     extra = "ignore"

# ============================================================
# Batch 응답
# ============================================================
class BatchResponse(BaseResponse):
    job_id: Optional[str] = None
    type: Optional[str] = None
    jobs: Optional[List[Dict[str, Any]]] = None  # 목록(그대로 dict 유지)
    job: Optional[JobStatus] = None              # 단일 Job 상세

# ============================================================
# Snapshot 응답
# ============================================================
class SnapshotResponse(BaseResponse):
    path: Optional[str] = None
    count: Optional[int] = None
    snapshots: Optional[List[str]] = None

# ============================================================
# Cache / BM25 / Admin 응답
# ============================================================
class AdminResponse(BaseResponse):
    detail: Optional[Dict[str, Any]] = None

# ============================================================
# Retrieve 응답
# ============================================================
class RetrieveResponse(BaseResponse):
    results: List[Dict[str, Any]]

# ============================================================
# Collection List 응답
# ============================================================
class CollectionInfo(BaseModel):
    name: str
    count: int
    vector_size: Optional[int] = None
    status: Optional[str] = None

class CollectionListResponse(BaseResponse):
    collections: List[CollectionInfo]
    total_count: int