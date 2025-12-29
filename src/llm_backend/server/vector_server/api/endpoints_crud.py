# llm_backend/server/vector_server/api/endpoints_crud.py
# -*- coding: utf-8 -*-
import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
import json
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.server.vector_server.models.request_models import (
    UpdatePayloadRequest, DeleteRequest, RetrieveRequest
)
from llm_backend.server.vector_server.models.response_models import CRUDResponse, RetrieveResponse
from llm_backend.server.vector_server.core.cache_manager import bump_collection_epoch
from llm_backend.utils.logger import logger

router = APIRouter(prefix="/crud", tags=["CRUD"])

@router.post("/upsert", response_model=CRUDResponse)
async def upsert_document(collection: str = Form(...), file: UploadFile = File(...)):
    try:
        contents = await file.read()
        data = json.loads(contents.decode("utf-8"))
        with acquire_manager() as mgr:
            await asyncio.to_thread(mgr.upsert_document, collection, data)
        bump_collection_epoch(collection)
        logger.info(f"[Upsert] '{file.filename}' → '{collection}' 업로드 완료")
        return CRUDResponse(status="success", collection=collection, filename=file.filename)
    except Exception as e:
        logger.error(f"[CRUD:/upsert] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/update", response_model=CRUDResponse)
async def update_document(req: UpdatePayloadRequest):
    try:
        with acquire_manager() as mgr:
            success = await asyncio.to_thread(
                mgr.update_payload, req.collection, req.db_id, req.new_payload, req.merge
            )
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        bump_collection_epoch(req.collection)
        return CRUDResponse(status="success", message=f"Updated {req.db_id[:10]}...")
    except Exception as e:
        logger.error(f"[CRUD:/update] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete", response_model=CRUDResponse)
async def delete_document(req: DeleteRequest):
    try:
        with acquire_manager() as mgr:
            success = await asyncio.to_thread(mgr.delete_document, req.collection, req.db_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        bump_collection_epoch(req.collection)
        return CRUDResponse(status="success", message=f"Deleted {req.db_id[:10]}...")
    except Exception as e:
        logger.error(f"[CRUD:/delete] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# Phase 4: Retrieve API
# ============================================================

@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_documents(req: RetrieveRequest):
    """
    여러 문서 원본 조회 (Batch)
    """
    try:
        with acquire_manager() as mgr:
            results = await asyncio.to_thread(mgr.get_documents, req.collection, req.db_ids)
        
        return RetrieveResponse(status="success", results=results)
    except Exception as e:
        logger.error(f"[CRUD:/retrieve] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{collection}/{db_id}", response_model=RetrieveResponse)
async def get_single_document(collection: str, db_id: str):
    """
    단일 문서 원본 조회
    """
    try:
        with acquire_manager() as mgr:
            res = await asyncio.to_thread(mgr.get_document, collection, db_id)
        
        if not res:
            raise HTTPException(status_code=404, detail="Document not found")
            
        return RetrieveResponse(status="success", results=[res])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CRUD:/document] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))