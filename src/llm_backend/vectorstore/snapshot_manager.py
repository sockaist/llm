"""Snapshot 관리 유틸리티 (Qdrant)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from llm_backend.utils.debug import trace
from llm_backend.utils.logger import logger
from llm_backend.vectorstore.config import SNAPSHOT_DIR


def _ensure_dir(dest_dir: str) -> None:
    Path(dest_dir).mkdir(parents=True, exist_ok=True)


def _is_under(base_dir: str, target: str) -> bool:
    base = Path(base_dir).resolve()
    tgt = Path(target).resolve()
    return str(tgt).startswith(str(base))


def create_snapshot(manager, collection: Optional[str] = None, dest_dir: str = SNAPSHOT_DIR) -> Dict[str, str]:
    trace("create_snapshot()")
    _ensure_dir(dest_dir)
    col = collection or getattr(manager, "default_collection", None) or "default"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_path = os.path.join(dest_dir, f"{col}_{ts}.zip")

    if not _is_under(dest_dir, snap_path):
        raise ValueError("Snapshot path must stay under dest_dir")

    try:
        logger.info(f"[Snapshot] Creating snapshot for '{col}'...")
        snapshot = manager.client.create_snapshot(collection_name=col, wait=True)
        snap_name = snapshot.name
        manager.client.download_snapshot(collection_name=col, snapshot_name=snap_name, path=snap_path)
        logger.info(f"[Snapshot] Saved snapshot to: {snap_path}")
        return {"status": "ok", "collection": col, "snapshot": snap_path}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Snapshot Error] {exc}")
        return {"status": "error", "detail": str(exc)}


def list_snapshots(manager, collection: Optional[str] = None, dest_dir: str = SNAPSHOT_DIR) -> List[Dict[str, str]]:
    trace("list_snapshots()")
    col = collection or getattr(manager, "default_collection", None) or "default"
    try:
        snapshots = manager.client.list_snapshots(collection_name=col)
        result = [{"name": s.name, "created": str(s.creation_time)} for s in snapshots]
        logger.info(f"[Snapshot] {len(result)} snapshots found for '{col}'")
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Snapshot List Error] {exc}")
        return []


def restore_snapshot(manager, collection: str, snapshot_path: str) -> Dict[str, str]:
    trace("restore_snapshot()")
    if not _is_under(SNAPSHOT_DIR, snapshot_path):
        return {"status": "error", "detail": "Snapshot path must be under SNAPSHOT_DIR"}

    if not os.path.exists(snapshot_path):
        return {"status": "error", "detail": f"Snapshot not found: {snapshot_path}"}

    try:
        logger.info(f"[Snapshot] Restoring collection '{collection}' from '{snapshot_path}'")
        manager.client.recover_snapshot(collection_name=collection, location=snapshot_path)
        logger.info(f"[Snapshot] '{collection}' successfully restored.")
        return {"status": "ok", "collection": collection}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Snapshot Restore Error] {exc}")
        return {"status": "error", "detail": str(exc)}


def delete_snapshot(manager, collection: str, snapshot_name: str) -> Dict[str, str]:
    trace("delete_snapshot()")
    try:
        logger.info(f"[Snapshot] Deleting snapshot '{snapshot_name}' from '{collection}'")
        manager.client.delete_snapshot(collection_name=collection, snapshot_name=snapshot_name)
        logger.info(f"[Snapshot] Deleted snapshot '{snapshot_name}'")
        return {"status": "ok", "deleted": snapshot_name}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Snapshot Delete Error] {exc}")
        return {"status": "error", "detail": str(exc)}
