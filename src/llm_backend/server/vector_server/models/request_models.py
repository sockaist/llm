# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


# ============================================================
# Query 요청
# ============================================================
class QueryRequest(BaseModel):
    query_text: str
    top_k: int = 5
    collections: Optional[List[str]] = None
    alpha: Optional[float] = None # 0.0 (Sparse) ~ 1.0 (Dense)
    tuning_mode: Optional[str] = "manual" # "manual", "auto", "heuristic"


# ============================================================
# CRUD 요청
# ============================================================
class UpdatePayloadRequest(BaseModel):
    collection: str
    db_id: str
    new_payload: Dict[str, Any]
    merge: bool = True


class DeleteRequest(BaseModel):
    collection: str
    db_id: str


# ============================================================
# Batch 요청
# ============================================================
class BatchUpsertRequest(BaseModel):
    folder: str
    collection: str


# ============================================================
# Admin / BM25 요청
# ============================================================
class BM25RetrainRequest(BaseModel):
    base_path: Optional[str] = "./data"


class SnapshotRestoreRequest(BaseModel):
    path: str
    
class SnapshotPathRequest(BaseModel):
    """
    스냅샷 파일 경로를 body로 전달할 때 사용.
    예: { "path": "./snapshots/notion.marketing_20251104_180000.snapshot" }
    """
    path: str


class SnapshotDeleteRequest(BaseModel):
    path: str
    
# 추가
class CreateCollectionRequest(BaseModel):
    name: str
    vector_size: int = 768

class DeleteCollectionRequest(BaseModel):
    name: str


# ============================================================
# Phase 4: Retrieve / Keyword Request Models
# ============================================================
class KeywordSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    
class RetrieveRequest(BaseModel):
    collection: str
    db_ids: List[str]