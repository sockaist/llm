# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from llm_backend.server.vector_server.core.queue_manager import (
    enqueue_job,
    get_job_status,
    list_jobs,
)
from llm_backend.server.vector_server.models.request_models import (
    AsyncBatchUpsertRequest,
    AsyncCreateCollectionRequest,
)
from llm_backend.server.vector_server.models.response_models import (
    BatchResponse,
    JobStatus,
)
from llm_backend.utils.logger import logger

from llm_backend.server.vector_server.core.auth import get_user_context_v2
from llm_backend.server.vector_server.core.security.access_control import Action, Role

logger.info("!!! ENDPOINTS_BATCH MODULE LOADED FROM DISK !!!")

router = APIRouter(prefix="/batch", tags=["Batch Jobs"])





@router.post("/ingest", response_model=BatchResponse, summary="Batch Ingest Documents (Async)")
async def upsert_batch_docs(
    req: AsyncBatchUpsertRequest,
    request: Request,
    user_context: dict = Depends(get_user_context_v2),
):
    """
    Queue a specific list of documents for asynchronous insertion.
    Use this for bulk data ingestion from client-side scripts.
    """
    try:
        logger.info(
            f"!!! ENDPOINT HIT [upsert_batch_docs]: user_context={user_context} !!!"
        )

        # Access Control
        if not hasattr(request.state, "access_manager"):
            logger.error("!!! ACCESS MANAGER MISSING IN STATE !!!")
            raise HTTPException(500, "Access Manager missing")

        access_manager = request.state.access_manager
        allowed, reason = access_manager.check_permission(
            user_context, {"collection": req.collection}, Action.WRITE
        )
        if not allowed:
            raise HTTPException(status_code=403, detail=f"Access Denied: {reason}")

        job_id = enqueue_job(
            job_type="upsert_batch_docs",
            payload={"collection": req.collection, "documents": req.documents},
        )
        logger.info(
            f"[Batch:/upsert_batch] Job queued (id={job_id[:8]}) for {req.collection}"
        )
        return BatchResponse(
            status="queued",
            job_id=job_id,
            message=f"Async upsert for {len(req.documents)} queued",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Batch:/upsert_batch] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create_collection", response_model=BatchResponse)
async def create_collection_async(
    req: AsyncCreateCollectionRequest,
    request: Request,
    user_context: dict = Depends(get_user_context_v2),
):
    """
    Queue collection creation as a background task.
    """
    try:
        # Access Control: Require ADMIN or ENGINEER for collection management
        _access_manager = request.state.access_manager
        user_role = user_context.get("user", {}).get("role")

        if user_role not in [Role.ADMIN, Role.ENGINEER]:
            raise HTTPException(
                status_code=403,
                detail="Access Denied: Insufficient permissions for collection management",
            )

        job_id = enqueue_job(
            job_type="create_collection",
            payload={"name": req.name, "vector_size": req.vector_size},
        )
        logger.info(
            f"[Batch:/create_collection] Job queued (id={job_id[:8]}) for {req.name}"
        )
        return BatchResponse(
            status="queued",
            job_id=job_id,
            message=f"Collection '{req.name}' creation queued",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Batch:/create_collection] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/status/{job_id}", response_model=BatchResponse)
async def get_job_status_api(
    job_id: str, request: Request, user_context: dict = Depends(get_user_context_v2)
):
    try:
        # Anyone authenticated can check status of their jobs?
        # For simplicity in MVP, allow any authenticated user, but ideally restrict to job owner or admin.
        st = get_job_status(job_id)
        if not st:
            raise HTTPException(status_code=404, detail="Job not found")

        logger.info(
            f"[Batch:/jobs/status] Queried job {job_id[:8]} -> {st.get('status')}"
        )
        filtered = {
            k: st.get(k)
            for k in ("id", "type", "status", "progress", "message", "created_at")
        }
        return BatchResponse(status="success", job=JobStatus(**filtered))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Batch:/jobs/status] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/list", response_model=BatchResponse)
async def list_jobs_api(
    request: Request,
    limit: Optional[int] = 10,
    user_context: dict = Depends(get_user_context_v2),
):
    try:
        # Restrict listing all jobs to Admins
        user_role = user_context.get("user", {}).get("role")
        if user_role != Role.ADMIN:
            raise HTTPException(
                status_code=403, detail="Access Denied: Only Admins can list all jobs"
            )

        jobs = list_jobs(limit)
        logger.info(f"[Batch:/jobs/list] Listed {len(jobs.get('jobs', []))} jobs")
        return BatchResponse(status="success", jobs=jobs.get("jobs", []))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Batch:/jobs/list] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
