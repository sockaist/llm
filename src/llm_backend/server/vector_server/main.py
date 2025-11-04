# -*- coding: utf-8 -*-
import os
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn

from llm_backend.vectorstore.vector_db_manager import VectorDBManager
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace


# -------------------------------------------------
# Pydantic 데이터 모델 정의
# -------------------------------------------------
class QueryRequest(BaseModel):
    query_text: str
    top_k: int = 5
    collections: Optional[List[str]] = None


class UpsertRequest(BaseModel):
    collection: str
    data: dict
    doc_id: Optional[str] = None


class UpdatePayloadRequest(BaseModel):
    collection: str
    doc_id: str
    new_payload: Dict[str, Any]
    merge: bool = True


class DeleteRequest(BaseModel):
    collection: str
    db_id: str


# -------------------------------------------------
# FastAPI 서버 정의
# -------------------------------------------------
app = FastAPI(title="Vector Manager API", version="1.1.0")
vector_manager: Optional[VectorDBManager] = None


# -------------------------------------------------
# 서버 시작 시 초기화
# -------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """
    서버 시작 시 VectorDBManager 초기화 및 BM25 자동 로드.
    BM25가 없으면 경고만 출력하고 계속 실행.
    """
    global vector_manager
    logger.info("[Startup] Initializing VectorDBManager...")
    trace("Starting Vector Server")

    try:
        vector_manager = VectorDBManager(default_collection="notion.marketing")
        bm25_path = "./models/bm25.pkl"

        # 1️⃣ BM25 자동 로드 시도
        if os.path.exists(bm25_path):
            from llm_backend.vectorstore.sparse_helper import load_bm25
            vector_manager.bm25_vectorizer = load_bm25(bm25_path)
            logger.info("[Startup] BM25 vectorizer loaded successfully.")
        else:
            logger.warning("[Startup] No BM25 model found — skipping fitting. "
                           "Use /fit_bm25 API later to train manually.")

        logger.info("[Startup] Vector Manager Ready ✅")

    except Exception as e:
        logger.error(f"[Startup Error] {e}")
        raise

@app.post("/build_index")
async def build_index(folder: str, collection: str):
    """
    지정한 폴더의 모든 JSON 문서를 기반으로 VectorDB 컬렉션 구축
    """
    global vector_manager
    try:
        count = await run_in_threadpool(
            lambda: vector_manager.upsert_folder(folder, collection)
        )
        return {"status": "ok", "message": f"{count} documents indexed into {collection}"}
    except Exception as e:
        logger.error(f"[API:build_index] {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------
# Health Check
# -------------------------------------------------
@app.get("/health")
async def health_check():
    """서버 상태 점검"""
    return {
        "status": "ok",
        "bm25_ready": hasattr(vector_manager, "bm25_vectorizer"),
        "default_collection": vector_manager.default_collection if vector_manager else None
    }


# -------------------------------------------------
# BM25 수동 학습 API
# -------------------------------------------------
@app.post("/fit_bm25")
async def fit_bm25(base_path: str = "./data"):
    """BM25 모델 수동 학습 (저장 포함)"""
    global vector_manager
    if vector_manager is None:
        raise HTTPException(status_code=500, detail="VectorManager not initialized")

    try:
        count = await run_in_threadpool(
            lambda: vector_manager.fit_bm25_from_json_folder(base_path)
        )
        from llm_backend.vectorstore.sparse_helper import save_bm25
        os.makedirs("./models", exist_ok=True)
        save_bm25(vector_manager.bm25_vectorizer, "./models/bm25.pkl")
        return {"status": "ok", "trained_docs": count, "path": base_path}
    except Exception as e:
        logger.error(f"[fit_bm25] Training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# 검색 API
# -------------------------------------------------
@app.post("/query")
async def query_docs(req: QueryRequest):
    """질의 수행"""
    try:
        results = await run_in_threadpool(
            lambda: vector_manager.query(
                query_text=req.query_text,
                top_k=req.top_k,
                collections=req.collections
            )
        )
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"[API:query] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# 업서트 API
# -------------------------------------------------
@app.post("/upsert")
async def upsert_doc(req: UpsertRequest):
    """문서 업서트"""
    try:
        await run_in_threadpool(
            lambda: vector_manager.upsert_document(req.collection, req.data, req.doc_id)
        )
        return {"status": "success", "message": f"Document upserted into {req.collection}"}
    except Exception as e:
        logger.error(f"[API:upsert] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# 페이로드 업데이트 API
# -------------------------------------------------
@app.patch("/update")
async def update_payload(req: UpdatePayloadRequest):
    """문서 payload 업데이트"""
    try:
        success = await run_in_threadpool(
            lambda: vector_manager.update_payload(
                req.collection, req.doc_id, req.new_payload, req.merge
            )
        )
        return {"status": "success" if success else "fail"}
    except Exception as e:
        logger.error(f"[API:update] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# 삭제 API
# -------------------------------------------------
@app.delete("/delete")
async def delete_doc(req: DeleteRequest):
    """문서 삭제"""
    try:
        success = await run_in_threadpool(
            lambda: vector_manager.delete_document(req.collection, req.db_id)
        )
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success", "message": f"Deleted {req.db_id} from {req.collection}"}
    except Exception as e:
        logger.error(f"[API:delete] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# 기본 루트
# -------------------------------------------------
@app.get("/")
async def root():
    return {"message": "Vector Manager Server is running 🚀"}


# -------------------------------------------------
# 실행
# -------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        app, host="127.0.0.1", port=8001, reload=True
    )