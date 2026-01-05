# llm_backend/server/vector_server/core/queue_manager.py
# -*- coding: utf-8 -*-
import threading
import time
import uuid
import sqlite3
import json
import os
from typing import Dict, Any, Optional
from llm_backend.utils.logger import logger

# Celery Import (Lazy or Top-level)
from llm_backend.server.vector_server.worker.tasks import process_job_task
from prometheus_client import Gauge

# --- Prometheus Metrics ---
JOB_QUEUE_GAUGE = Gauge("vortex_job_queue_count", "Number of jobs in queue")
JOB_ACTIVE_GAUGE = Gauge("vortex_job_active_count", "Number of active jobs")
JOB_FAILED_GAUGE = Gauge("vortex_job_failed_count", "Number of failed jobs")
JOB_COMPLETED_GAUGE = Gauge("vortex_job_completed_count", "Number of completed jobs")

# --- Advanced Monitoring Metrics ---
LAST_SNAPSHOT_GAUGE = Gauge("vortex_last_snapshot_timestamp", "Timestamp of the last successful snapshot")
LAST_BM25_GAUGE = Gauge("vortex_last_bm25_training_timestamp", "Timestamp of the last successful BM25 training")
USER_COUNT_GAUGE = Gauge("vortex_user_count_total", "Total number of users by role", ["role"])

# --- DB 설정 ---
DB_PATH = os.getenv("JOBS_DB_PATH", "./.vortex/db/jobs.db")
_stop_event = threading.Event()


def _get_connection():
    # Increase timeout to 30s for concurrent access
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                progress REAL DEFAULT 0.0,
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_status_created ON jobs (status, created_at)"
        )
        conn.commit()


# 초기화 (import 시 실행)
_init_db()

# Migration: Add 'progress' column if missing
# Migration: Add 'progress' column if missing
try:
    with _get_connection() as conn:
        conn.execute("ALTER TABLE jobs ADD COLUMN progress REAL DEFAULT 0.0")
        conn.commit()
except Exception:
    pass


def is_job_active(job_type: str) -> bool:
    """같은 타입의 작업이 queued/running 상태인지 확인"""
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM jobs WHERE type = ? AND status IN ('queued', 'running') LIMIT 1",
            (job_type,),
        )
        return cursor.fetchone() is not None


def last_completed_at(job_type: str) -> Optional[float]:
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT updated_at FROM jobs WHERE type = ? AND status = 'completed' ORDER BY updated_at DESC LIMIT 1",
            (job_type,),
        )
        row = cursor.fetchone()
        return row["updated_at"] if row else None


def enqueue_job(job_type: str, payload: Dict[str, Any]) -> str:
    # bm25_retrain 중복 방지
    if job_type == "bm25_retrain" and is_job_active("bm25_retrain"):
        logger.warning("bm25_retrain already queued or running")
        raise RuntimeError("bm25_retrain already queued or running")

    job_id = str(uuid.uuid4())
    now = time.time()

    with _get_connection() as conn:
        conn.execute(
            """INSERT INTO jobs (id, type, payload, status, message, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                job_type,
                json.dumps(payload),
                "queued",
                "Waiting for Celery Worker",
                now,
                now,
            ),
        )
        conn.commit()

    # Dispatch to Celery
    try:
        process_job_task.delay(job_id, job_type, payload)
        logger.info(f"[Queue] Job dispatched to Celery: {job_type} (id={job_id[:8]})")
    except Exception as e:
        logger.error(f"[Queue] Failed to dispatch to Celery: {e}")
        # Update DB to failed? Or leave keyed to retry?
        # Let's mark failed to be safe.
        with _get_connection() as conn:
            conn.execute(
                "UPDATE jobs SET status='failed', message=? WHERE id=?",
                (f"Dispatch Error: {e}", job_id),
            )
            conn.commit()
        raise e

    return job_id


# Phase 2: No internal worker loop. We rely on external Celery worker.
def start_worker():
    logger.info(
        "[QueueWorker] Running in Distributed Mode (Phase 2). Internal worker thread is DISABLED."
    )
    logger.info(
        "[QueueWorker] Please ensure you are running 'celery -A llm_backend.server.vector_server.worker.celery_app worker --loglevel=info'"
    )


def stop_worker():
    logger.info("[QueueWorker] Stop signal ignored (No internal worker)")


def get_job_status(job_id: str) -> Dict[str, Any]:
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, type, status, message, progress, created_at, updated_at FROM jobs WHERE id = ?",
            (job_id,),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {"status": "unknown", "message": "No such job"}


def list_jobs(limit: int = 20) -> Dict[str, Any]:
    with _get_connection() as conn:
        # Get counts by status
        counts = {}
        for status in ["queued", "running", "completed", "failed"]:
            c = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE status = ?", (status,)
            ).fetchone()[0]
            counts[status] = c

        # Get recent jobs
        cursor = conn.execute(
            "SELECT id, type, status, message, progress, created_at, updated_at FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        return {"counts": counts, "jobs": rows}

def collect_metrics():
    """Update Prometheus metrics from DB stats."""
    try:
        with _get_connection() as conn:
            # Get counts by status
            for status, gauge in [
                ("queued", JOB_QUEUE_GAUGE),
                ("running", JOB_ACTIVE_GAUGE),
                ("failed", JOB_FAILED_GAUGE),
                ("completed", JOB_COMPLETED_GAUGE)
            ]:
                c = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status = ?", (status,)
                ).fetchone()[0]
                gauge.set(c)
    except Exception as e:
        logger.error(f"[Metrics] Failed to collect job metrics: {e}")

def collect_advanced_metrics():
    """Update advanced metrics (timestamps, user counts)."""
    try:
        with _get_connection() as conn:
            # 1) Latest Snapshot
            cursor = conn.execute(
                "SELECT updated_at FROM jobs WHERE (type = 'create_snapshot' OR type = 'snapshot_cycle') AND status = 'completed' ORDER BY updated_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                LAST_SNAPSHOT_GAUGE.set(row["updated_at"])

            # 2) Latest BM25
            cursor = conn.execute(
                "SELECT updated_at FROM jobs WHERE type = 'bm25_retrain' AND status = 'completed' ORDER BY updated_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                LAST_BM25_GAUGE.set(row["updated_at"])

        # 3) User Counts
        from vectordb.core.security.db import UserManager
        manager = UserManager()
        users = manager.list_users()
        
        counts = {}
        for user in users:
            role = user.role
            counts[role] = counts.get(role, 0) + 1
        
        for role, count in counts.items():
            USER_COUNT_GAUGE.labels(role=role).set(count)

    except Exception as e:
        logger.error(f"[Metrics] Failed to collect advanced metrics: {e}")
