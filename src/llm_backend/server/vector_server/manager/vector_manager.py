# llm_backend/server/vector_server/manager/vector_manager.py
# -*- coding: utf-8 -*-
import os
from llm_backend.vectorstore.vector_db_manager import VectorDBManager
from llm_backend.utils.logger import logger
from llm_backend.vectorstore.config import (
    SNAPSHOT_DIR,
    VECTOR_SIZE,
    DEFAULT_COLLECTION_NAME,
)


def _extend_auto_initialize():
    def auto_initialize(
        self, base_folder: str = "./data", snapshot_dir: str = SNAPSHOT_DIR
    ):
        from llm_backend.server.vector_server.manager.snapshot_manager import (
            list_snapshots,
            restore_snapshot,
            create_snapshot,
        )

        try:
            os.makedirs(snapshot_dir, exist_ok=True)
            snapshots = sorted(list_snapshots(), key=os.path.getmtime, reverse=True)
            if snapshots:
                latest_snapshot = snapshots[0]
                logger.info(f"[AutoInit] Restoring latest snapshot: {latest_snapshot}")
                restore_snapshot(latest_snapshot)
                logger.info("[AutoInit] Snapshot restored successfully")
                return
            logger.warning("[AutoInit] No snapshot found — initializing new collection")

            if not hasattr(self, "default_collection") or not self.default_collection:
                self.default_collection = DEFAULT_COLLECTION_NAME
            self.create_collection(self.default_collection, vector_size=VECTOR_SIZE)

            data_path = os.path.join(base_folder, self.default_collection)
            if os.path.exists(data_path):
                logger.info(f"[AutoInit] Uploading data from {data_path}")
                self.upsert_folder(data_path, self.default_collection)
                logger.info("[AutoInit] Folder upload complete")
            else:
                logger.warning(
                    f"[AutoInit] No data folder at {data_path}, skipping upsert"
                )

            logger.info("[AutoInit] Fitting BM25 model...")
            self.fit_bm25_from_json_folder(base_folder)
            logger.info("[AutoInit] BM25 model ready")

            snapshot_path = create_snapshot(self.default_collection)
            logger.info(f"[AutoInit] Initial snapshot created at {snapshot_path}")
        except Exception as e:
            logger.error(f"[AutoInit] Initialization failed: {e}")
            raise

    setattr(VectorDBManager, "auto_initialize", auto_initialize)


_extend_auto_initialize()


def run_server_auto_initialize(
    default_collection=DEFAULT_COLLECTION_NAME,
    base_folder="./data",
    snapshot_dir=SNAPSHOT_DIR,
):
    """
    서버 부팅 시 1회만 호출: 스냅샷 복원 또는 초기화 + BM25 + 스냅샷 생성
    """
    try:
        mgr = VectorDBManager(default_collection=default_collection)
        mgr.auto_initialize(base_folder=base_folder, snapshot_dir=snapshot_dir)
        logger.info("[VectorManager] Auto-initialize completed")
    except Exception as e:
        logger.error(f"[VectorManager] Auto-initialize failed: {e}")
        raise
