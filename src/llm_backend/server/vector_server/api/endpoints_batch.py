# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from typing import Optional
from llm_backend.server.vector_server.core.queue_manager import (
    enqueue_job, get_job_status, list_jobs
)
from llm_backend.server.vector_server.models.request_models import BatchUpsertRequest
from llm_backend.server.vector_server.models.response_models import BatchResponse, JobStatus
from llm_backend.utils.logger import logger

router = APIRouter(prefix="/batch", tags=["Batch Jobs"])

@router.post("/upsert", response_model=BatchResponse)
async def batch_upsert(req: BatchUpsertRequest):
    try:
        job_id = enqueue_job(
            job_type="batch_upsert",
            payload={"folder": req.folder, "collection": req.collection}
        )
        logger.info(f"[Batch:/upsert] Job queued (id={job_id[:8]}) for {req.collection}")
        return BatchResponse(
            status="queued",
            job_id=job_id,
            message=f"Batch upsert for '{req.collection}' queued successfully"
        )
    except Exception as e:
        logger.error(f"[Batch:/upsert] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/status/{job_id}", response_model=BatchResponse)
async def get_job_status_api(job_id: str):
    try:
        st = get_job_status(job_id)
        if not st:
            raise HTTPException(status_code=404, detail="Job not found")
        logger.info(f"[Batch:/jobs/status] Queried job {job_id[:8]} → {st.get('status')}")
        # 필요한 필드만 추려서 안전하게 매핑
        filtered = {k: st.get(k) for k in ("id","type","status","progress","message","created_at")}
        return BatchResponse(status="success", job=JobStatus(**filtered))
    except Exception as e:
        logger.error(f"[Batch:/jobs/status] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/list", response_model=BatchResponse)
async def list_jobs_api(limit: Optional[int] = 10):
    try:
        jobs = list_jobs(limit)
        logger.info(f"[Batch:/jobs/list] Listed {len(jobs.get('jobs', []))} jobs")
        # 목록은 기존 스키마 유지 (dict 리스트)
        return BatchResponse(status="success", jobs=jobs.get("jobs", []))
    except Exception as e:
        logger.error(f"[Batch:/jobs/list] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))