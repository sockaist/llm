# llm_backend/server/vector_server/worker/tasks.py
import time
import sqlite3
import traceback
from llm_backend.server.vector_server.worker.celery_app import celery_app
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.utils.logger import logger

# Helper to update SQLite status from Celery Worker
# NOTE: Celery worker must have access to the same ./data path or use a shared DB.
# Since this is "local distributed" (same machine), file path works.
DB_PATH = "./data/jobs.db"

def _update_job_status(job_id, status, message=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, message = COALESCE(?, message), updated_at = ? WHERE id = ?",
                (status, message, time.time(), job_id)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"[Task] Failed to update DB status for {job_id}: {e}")

@celery_app.task(bind=True)
def process_job_task(self, job_id: str, job_type: str, payload: dict):
    logger.info(f"[Celery] Processing job {job_id} ({job_type})")
    
    # 1. Update Status -> Running
    _update_job_status(job_id, "running", "Processing in Celery Worker...")

    try:
        if job_type == "batch_upsert":
            folder = payload.get("folder")
            collection = payload.get("collection")
            batch_size = payload.get("batch_size", 50)
            if folder and collection:
                with acquire_manager() as mgr:
                    # Note: upsert_folder logs progress to python logger, which might not show up in celery console unless configured
                    mgr.upsert_folder(folder, collection, batch_size=batch_size)
        
        elif job_type == "bm25_retrain":
            base_path = payload.get("base_path", "./data")
            with acquire_manager() as mgr:
                if hasattr(mgr, "init_bm25"):
                    mgr.init_bm25(base_path, force_retrain=True)
                else:
                    mgr.fit_bm25_from_json_folder(base_path)
        
        else:
            raise ValueError(f"Unknown job type: {job_type}")

        # 2. Update Status -> Completed
        _update_job_status(job_id, "completed", "Job completed successfully")
        logger.info(f"[Celery] Job {job_id} completed")
        return "success"

    except Exception as e:
        # 3. Update Status -> Failed
        error_msg = f"Error: {str(e)}"
        _update_job_status(job_id, "failed", error_msg)
        logger.error(f"[Celery] Job {job_id} failed: {e}\n{traceback.format_exc()}")
        self.retry(exc=e, countdown=60, max_retries=3)  # Optional: Retry logic
