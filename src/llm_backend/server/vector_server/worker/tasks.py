# llm_backend/server/vector_server/worker/tasks.py
import time
import sqlite3
import traceback
import os
from llm_backend.server.vector_server.worker.celery_app import celery_app
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.utils.logger import logger

# Helper to update SQLite status from Celery Worker
# NOTE: Celery worker must have access to the same ./data path or use a shared DB.
# Since this is "local distributed" (same machine), file path works.
DB_PATH = os.getenv("JOBS_DB_PATH", "./.vortex/db/jobs.db")


def _update_job_status(job_id, status, message=None, progress=None):
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            if progress is not None:
                conn.execute(
                    "UPDATE jobs SET status = ?, message = COALESCE(?, message), progress = ?, updated_at = ? WHERE id = ?",
                    (status, message, progress, time.time(), job_id),
                )
            else:
                conn.execute(
                    "UPDATE jobs SET status = ?, message = COALESCE(?, message), updated_at = ? WHERE id = ?",
                    (status, message, time.time(), job_id),
                )
            conn.commit()
    except Exception as e:
        logger.error(f"[Task] Failed to update DB status for {job_id}: {e}")


@celery_app.task(bind=True)
def process_job_task(self, job_id: str, job_type: str, payload: dict):
    logger.info(f"[Celery] Processing job {job_id} ({job_type})")

    # 1. Update Status -> Running
    _update_job_status(
        job_id, "running", "Processing in Celery Worker...", progress=0.0
    )

    try:
        if job_type == "batch_upsert":
            folder = payload.get("folder")
            collection = payload.get("collection")
            batch_size = payload.get("batch_size", 50)
            if folder and collection:
                with acquire_manager() as mgr:

                    def progress_cb(p: float):
                        _update_job_status(job_id, "running", progress=p)

                    mgr.upsert_folder(
                        folder,
                        collection,
                        batch_size=batch_size,
                        progress_callback=progress_cb,
                    )

        elif job_type == "upsert_batch_docs":
            collection = payload.get("collection")
            documents = payload.get("documents", [])
            with acquire_manager() as mgr:

                def progress_cb(p: float):
                    _update_job_status(job_id, "running", progress=p)

                mgr.upsert_documents(
                    collection, documents, progress_callback=progress_cb
                )

        elif job_type == "create_collection":
            name = payload.get("name")
            vector_size = payload.get("vector_size", 1024)
            with acquire_manager() as mgr:
                mgr.create_collection(name, vector_size=vector_size)

        elif job_type == "bm25_retrain":
            base_path = payload.get("base_path", "./data")
            with acquire_manager() as mgr:
                if hasattr(mgr, "init_bm25"):
                    mgr.init_bm25(base_path, force_retrain=True)
                else:
                    mgr.fit_bm25_from_json_folder(base_path)

        elif job_type == "create_snapshot":
            collection = payload.get("collection")
            with acquire_manager() as mgr:
                path = mgr.create_snapshot(collection=collection)
                # Store the result path in the message or a separate result field if DB supported it.
                # For now, put it in the success message.
                _update_job_status(
                    job_id, "completed", f"Snapshot created at {path}", progress=100.0
                )
                return "success"

        else:
            raise ValueError(f"Unknown job type: {job_type}")

        # 2. Update Status -> Completed (If not already updated inside specific handler)
        # Note: create_snapshot updates it manually above to include path, but safe to update again if needed
        # or just return. Let's make it consistent.
        if job_type != "create_snapshot":
             _update_job_status(
                job_id, "completed", "Job completed successfully", progress=100.0
            )
        
        logger.info(f"[Celery] Job {job_id} completed")
        return "success"

    except Exception as e:
        # 3. Update Status -> Failed
        error_msg = f"Error: {str(e)}"
        _update_job_status(job_id, "failed", error_msg)
        logger.error(f"[Celery] Job {job_id} failed: {e}\n{traceback.format_exc()}")
        self.retry(exc=e, countdown=60, max_retries=3)  # Optional: Retry logic


@celery_app.task(bind=True)
def upsert_batch_docs_task(self, job_id: str, collection: str, documents: list):
    logger.info(f"[Celery] Processing batch upsert {job_id} for {collection}")
    _update_job_status(job_id, "running", f"Upserting {len(documents)} docs...")
    try:
        with acquire_manager() as mgr:

            def progress_cb(p: float):
                _update_job_status(job_id, "running", progress=p)

            count = mgr.upsert_documents(
                collection, documents, progress_callback=progress_cb
            )
        _update_job_status(
            job_id, "completed", f"Successfully upserted {count} docs", progress=100.0
        )
        return "success"
    except Exception as e:
        _update_job_status(job_id, "failed", str(e))
        logger.error(f"[Celery] Batch upsert {job_id} failed: {e}")
        raise


@celery_app.task(bind=True)
def create_collection_task(self, job_id: str, name: str, vector_size: int):
    logger.info(f"[Celery] Creating collection {name} (size={vector_size})")
    _update_job_status(job_id, "running", "Creating collection and indexing...")
    try:
        with acquire_manager() as mgr:
            mgr.create_collection(name, vector_size=vector_size)
        _update_job_status(job_id, "completed", f"Collection '{name}' created")
        return "success"
    except Exception as e:
        _update_job_status(job_id, "failed", str(e))
        logger.error(f"[Celery] Create collection {job_id} failed: {e}")
        raise


@celery_app.task(bind=True)
def create_snapshot_task(self, job_id: str, collection: str):
    logger.info(f"[Celery] Creating snapshot for {collection}")
    _update_job_status(job_id, "running", "Creating snapshot...")
    try:
        with acquire_manager() as mgr:
            path = mgr.create_snapshot(collection=collection)
        _update_job_status(
            job_id, "completed", f"Snapshot created: {os.path.basename(path)}", progress=100.0
        )
        return "success"
    except Exception as e:
        _update_job_status(job_id, "failed", str(e))
        logger.error(f"[Celery] Snapshot creation {job_id} failed: {e}")
        raise
