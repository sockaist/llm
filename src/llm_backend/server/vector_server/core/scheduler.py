# llm_backend/server/vector_server/core/scheduler.py
# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from llm_backend.utils.logger import logger
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.server.vector_server.manager.snapshot_manager import (
    create_snapshot,
    list_snapshots,
    delete_snapshot,
)
from llm_backend.server.vector_server.core.queue_manager import is_job_active, collect_metrics
from llm_backend.vectorstore.config import DEFAULT_COLLECTION_NAME

# ============================================================
# Scheduler 설정
# ============================================================

scheduler = BackgroundScheduler(timezone="Asia/Seoul")

# 스냅샷/보존 기본 설정 (환경변수로 오버라이드 가능)
SNAPSHOT_COLLECTION = os.getenv("SNAPSHOT_COLLECTION", DEFAULT_COLLECTION_NAME)
SNAPSHOT_RETENTION_DAYS = int(os.getenv("SNAPSHOT_RETENTION_DAYS", "30"))

# 주기 설정 (환경변수)
BM25_INTERVAL_MIN = int(os.getenv("BM25_INTERVAL_MIN", "60"))  # 분 단위
SNAPSHOT_INTERVAL_H = int(os.getenv("SNAPSHOT_INTERVAL_H", "12"))  # 시간 단위
BM25_BASE_PATH = os.getenv("BM25_BASE_PATH", "./data")


# ------------------------------------------------------------
# BM25 재학습
# ------------------------------------------------------------
def retrain_bm25():
    """
    BM25 모델 재학습.
    - 큐에 동일 타입 작업이 활성화되어 있으면 스킵(중복 방지)
    """
    try:
        if is_job_active("bm25_retrain"):
            logger.info(
                "[Scheduler] Skip BM25 retrain: another bm25 job is queued/running"
            )
            return
        with acquire_manager() as mgr:
            # 구현에 따라 init_bm25(force_retrain=True) 가 있으면 선호
            if hasattr(mgr, "init_bm25"):
                mgr.init_bm25(BM25_BASE_PATH, force_retrain=True)
            else:
                mgr.fit_bm25_from_json_folder(BM25_BASE_PATH)
        logger.info("[Scheduler] BM25 model retrained successfully")
    except Exception as e:
        logger.error(f"[Scheduler] BM25 retraining failed: {e}")


# ------------------------------------------------------------
# 스냅샷 생성 + 오래된 스냅샷 자동 삭제
# ------------------------------------------------------------
def create_and_cleanup_snapshot():
    """
    스냅샷 생성 및 보존 기간 경과분 자동 삭제
    """
    try:
        # 새로운 스냅샷 생성
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        snapshot_path = create_snapshot(SNAPSHOT_COLLECTION)
        logger.info(
            f"[Scheduler] Snapshot created successfully at {timestamp} → {snapshot_path}"
        )

        # 오래된 스냅샷 삭제
        all_snapshots = list_snapshots()
        threshold_date = datetime.now() - timedelta(days=SNAPSHOT_RETENTION_DAYS)

        for path in all_snapshots:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime < threshold_date:
                    delete_snapshot(path)
                    logger.info(f"[Scheduler] Deleted old snapshot: {path}")
            except Exception as e:
                logger.warning(
                    f"[Scheduler] Failed to check or delete snapshot {path}: {e}"
                )

    except Exception as e:
        logger.error(f"[Scheduler] Snapshot creation failed: {e}")


# ------------------------------------------------------------
# 스케줄러 시작 (RUN_SCHEDULER 가드 + 잡 중복 방지)
# ------------------------------------------------------------
def start_scheduler():
    """
    APScheduler를 백그라운드로 실행합니다.
    - RUN_SCHEDULER != "1" 이면 시작하지 않음 (멀티프로세스 중복 방지)
    - 같은 id의 잡이 이미 있으면 중복 추가하지 않음
    - 간격은 BM25_INTERVAL_MIN(분), SNAPSHOT_INTERVAL_H(시간) 환경변수로 조절
    """
    try:
        if os.getenv("RUN_SCHEDULER", "1") != "1":
            logger.info("[Scheduler] RUN_SCHEDULER!=1 → skipping scheduler start")
            return

        if not scheduler.running:
            # BM25 재학습 주기 설정 (분 단위)
            if scheduler.get_job("bm25_retrain") is None:
                scheduler.add_job(
                    retrain_bm25,
                    "interval",
                    minutes=BM25_INTERVAL_MIN,
                    id="bm25_retrain",
                    coalesce=True,  # 누락된 실행은 1회로 합침
                    max_instances=1,
                )
                logger.info(
                    f"[Scheduler] Job 'bm25_retrain' scheduled every {BM25_INTERVAL_MIN} min"
                )
            else:
                logger.info("[Scheduler] Job 'bm25_retrain' already exists")

            # 스냅샷 생성 주기 설정 (시간 단위)
            if scheduler.get_job("snapshot_cycle") is None:
                scheduler.add_job(
                    create_and_cleanup_snapshot,
                    "interval",
                    hours=SNAPSHOT_INTERVAL_H,
                    id="snapshot_cycle",
                    coalesce=True,
                    max_instances=1,
                )
                logger.info(
                    f"[Scheduler] Job 'snapshot_cycle' scheduled every {SNAPSHOT_INTERVAL_H} h"
                )
            else:
                logger.info("[Scheduler] Job 'snapshot_cycle' already exists")

            # 메트릭 수집 주기 설정 (초 단위, 30초)
            if scheduler.get_job("job_metrics_collection") is None:
                from llm_backend.server.vector_server.core.queue_manager import collect_advanced_metrics
                scheduler.add_job(
                    lambda: (collect_metrics(), collect_advanced_metrics()),
                    "interval",
                    seconds=30,
                    id="job_metrics_collection",
                    coalesce=True,
                    max_instances=1,
                )
                logger.info("[Scheduler] Job 'job_metrics_collection' scheduled every 30s")
            else:
                logger.info("[Scheduler] Job 'job_metrics_collection' already exists")

            scheduler.start()
            logger.info("[Scheduler] APScheduler started successfully")
        else:
            logger.warning("[Scheduler] Scheduler already running")

    except Exception as e:
        logger.error(f"[Scheduler] Failed to start APScheduler: {e}")


# ------------------------------------------------------------
# 스케줄러 종료 (graceful)
# ------------------------------------------------------------
def stop_scheduler():
    """
    APScheduler를 안전하게 종료합니다.
    """
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("[Scheduler] APScheduler stopped")
        else:
            logger.info("[Scheduler] Scheduler not running")
    except Exception as e:
        logger.error(f"[Scheduler] Failed to stop APScheduler: {e}")


# ------------------------------------------------------------
# 수동 실행 (테스트용)
# ------------------------------------------------------------
if __name__ == "__main__":
    logger.info("[Scheduler] Manual start test")
    start_scheduler()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_scheduler()
        logger.info("[Scheduler] Stopped manually")
