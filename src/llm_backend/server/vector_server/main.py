# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn
import os

from llm_backend.vectorstore.vector_db_manager import VectorDBManager
from llm_backend.utils.logger import logger

# ---------------------------
# 서버 초기화
# ---------------------------
app = FastAPI(title="VectorDBManager Server", version="1.0.0")

# VectorDBManager 싱글톤 인스턴스
vector_manager = None


@app.on_event("startup")
def startup_event():
    global vector_manager
    try:
        logger.info("[Startup] Initializing VectorDBManager server...")
        vector_manager = VectorDBManager(default_collection="notion.marketing")
        vector_manager.init_bm25(base_path="./data", force_retrain=False)
        logger.info("[Startup] VectorDBManager initialized successfully.")
    except Exception as e:
        logger.error(f"[Startup Error] {e}")
        raise


# ---------------------------
# Request/Response Schema
# ---------------------------
class UpsertRequest(BaseModel):
    collection: str
    data: dict
    doc_id: Optional[str] = None


class QueryRequest(BaseModel):
    query_text: str
    top_k: int = 5
    collections: Optional[List[str]] = None


class DeleteRequest(BaseModel):
    collection: str
    db_id: str


# ---------------------------
# CRUD Endpoints
# ---------------------------

@app.post("/upsert")
def upsert_document(req: UpsertRequest):
    """단일 문서 업서트"""
    try:
        vector_manager.upsert_document(req.collection, req.data, req.doc_id)
        return {"status": "success", "message": f"Upserted document in {req.collection}"}
    except Exception as e:
        logger.error(f"[API:upsert] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
def query_vector(req: QueryRequest):
    """텍스트 기반 검색"""
    try:
        results = vector_manager.query(
            query_text=req.query_text,
            top_k=req.top_k,
            collections=req.collections,
        )
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"[API:query] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete")
def delete_document(req: DeleteRequest):
    """db_id 기반 문서 삭제"""
    try:
        success = vector_manager.delete_document(req.collection, req.db_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found or failed to delete.")
        return {"status": "success", "message": f"Deleted {req.db_id} from {req.collection}"}
    except Exception as e:
        logger.error(f"[API:delete] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok", "bm25_loaded": True}


# ---------------------------
# 메인 실행
# ---------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)