"""Snapshot 관리 유틸리티 (Qdrant)."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from llm_backend.utils.debug import trace
from llm_backend.utils.logger import logger
from llm_backend.vectorstore.config import SNAPSHOT_DIR


def _ensure_dir(dest_dir: str) -> None:
    Path(dest_dir).mkdir(parents=True, exist_ok=True)


def _is_under(base_dir: str, target: str) -> bool:
    base = Path(base_dir).resolve()
    tgt = Path(target).resolve()
    return str(tgt).startswith(str(base))


def _manual_download_snapshot(
    manager, collection_name: str, snapshot_name: str, out_path: str
):
    """Fallback manual download using requests."""
    # Try to get URL/API key from client config or env
    # manager.client usually has .http.client.base_url or similar but implementation varies.
    # Safe bet: utilize environment variables or assume default local docker logic
    base_url = os.getenv("QDRANT_URL", "http://vortex_qdrant:6333").rstrip("/")
    # If running inside same network, vortex_qdrant is the host.
    # The previous file used localhost, but this is server code running in container.
    
    api_key = os.getenv("QDRANT_API_KEY")

    url = f"{base_url}/collections/{collection_name}/snapshots/{snapshot_name}"
    headers = {}
    if api_key:
        headers["api-key"] = api_key

    logger.info(f"[Snapshot] Manual download from {url} to {out_path}")
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def create_snapshot(
    manager, collection: Optional[str] = None, dest_dir: str = SNAPSHOT_DIR
) -> Dict[str, str]:
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
        snap_name = getattr(snapshot, "name", None) or str(snapshot)
        if not isinstance(snap_name, str):
            # In some versions it might be an object, try simple cast or property
             snap_name = str(snapshot)

        # Try client download, fallback to manual
        try:
            if hasattr(manager.client, "download_snapshot"):
                manager.client.download_snapshot(
                    collection_name=col, snapshot_name=snap_name, path=snap_path
                )
            else:
                raise AttributeError("download_snapshot missing")
        except (AttributeError, TypeError, ValueError):
            logger.warning("[Snapshot] Client download failed. Using manual fallback.")
            _manual_download_snapshot(manager, col, snap_name, snap_path)

        logger.info(f"[Snapshot] Saved snapshot to: {snap_path}")
        return {"status": "ok", "collection": col, "snapshot": snap_path}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Snapshot Error] {exc}")
        return {"status": "error", "detail": str(exc)}


def list_snapshots(
    manager, collection: Optional[str] = None, dest_dir: str = SNAPSHOT_DIR
) -> List[Dict[str, str]]:
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
        logger.info(
            f"[Snapshot] Restoring collection '{collection}' from '{snapshot_path}'"
        )
        manager.client.recover_snapshot(
            collection_name=collection, location=snapshot_path
        )
        logger.info(f"[Snapshot] '{collection}' successfully restored.")
        return {"status": "ok", "collection": collection}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Snapshot Restore Error] {exc}")
        return {"status": "error", "detail": str(exc)}


def delete_snapshot(manager, collection: str, snapshot_name: str) -> Dict[str, str]:
    trace("delete_snapshot()")
    try:
        logger.info(
            f"[Snapshot] Deleting snapshot '{snapshot_name}' from '{collection}'"
        )
        manager.client.delete_snapshot(
            collection_name=collection, snapshot_name=snapshot_name
        )
        logger.info(f"[Snapshot] Deleted snapshot '{snapshot_name}'")
        return {"status": "ok", "deleted": snapshot_name}
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Snapshot Delete Error] {exc}")
        return {"status": "error", "detail": str(exc)}
