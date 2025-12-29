# llm_backend/server/vector_server/manager/snapshot_manager.py
# -*- coding: utf-8 -*-
import os
import requests
from typing import Optional
from pathlib import Path
from datetime import datetime
from qdrant_client import QdrantClient
from llm_backend.utils.logger import logger
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.config import SNAPSHOT_DIR

def _ensure_snapshot_dir():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def _is_under_snapshot_dir(path: str) -> bool:
    base = Path(SNAPSHOT_DIR).resolve()
    target = Path(path).resolve()
    return str(target).startswith(str(base))

def _manual_download_snapshot(client: QdrantClient, collection_name: str, snapshot_name: str, out_path: str):
    """
    Manually download snapshot via REST API when client helper is missing.
    """
    # 1. Base URL 추론
    # QdrantClient 인스턴스에서 URL을 꺼내오기 어렵다면 환경변수 우선 사용
    base_url = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
    api_key = os.getenv("QDRANT_API_KEY")

    url = f"{base_url}/collections/{collection_name}/snapshots/{snapshot_name}"
    headers = {}
    if api_key:
        headers["api-key"] = api_key
        
    logger.info(f"[Snapshot] Downloading manually from {url}")
    
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
def _manual_upload_snapshot(client: QdrantClient, collection_name: str, file_path: str):
    """
    Manually upload and restore snapshot via REST API.
    Qdrant's /upload endpoint uploads AND restores the collection from the file.
    """
    base_url = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
    api_key = os.getenv("QDRANT_API_KEY")
    url = f"{base_url}/collections/{collection_name}/snapshots/upload"
    headers = {}
    if api_key:
        headers["api-key"] = api_key
        
    logger.info(f"[Snapshot] Uploading and restoring from {file_path}")
    try:
        with open(file_path, "rb") as f:
            files = {"snapshot": (os.path.basename(file_path), f)}
            # priority param might be needed? Default usually works.
            resp = requests.post(url, headers=headers, files=files, params={"priority": "snapshot"})
            resp.raise_for_status()
            logger.info(f"[Snapshot] Upload/Restore response: {resp.text}")
    except Exception as e:
        logger.error(f"[Snapshot] Upload failed: {e}")
        raise
def create_snapshot(collection_name: str, path: Optional[str] = None) -> str:
    try:
        _ensure_snapshot_dir()

        # 1) 출력 경로 결정 + 화이트리스트 검사
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if path:
            # 사용자가 경로를 넘긴 경우: 반드시 SNAPSHOT_DIR 내부여야 함
            # (디렉터리를 준 경우를 대비해 파일명 자동 부여)
            cand = Path(path)
            if cand.suffix == "" and (cand.is_dir() or str(path).endswith(os.sep)):
                cand = cand / f"{collection_name}_{ts}.snapshot"
            out_path = str(cand)

            if not _is_under_snapshot_dir(out_path):
                raise ValueError("Snapshot path must be under SNAPSHOT_DIR")
        else:
            # 기본 경로: SNAPSHOT_DIR/<collection>_<timestamp>.snapshot
            out_path = os.path.join(SNAPSHOT_DIR, f"{collection_name}_{ts}.snapshot")

        # 상위 디렉터리 보장
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        # 2) 스냅샷 생성 후 로컬 다운로드
        with acquire_manager() as mgr:
            client: QdrantClient = mgr.client
            desc = client.create_snapshot(collection_name=collection_name)
            snap_name = getattr(desc, "name", None) or str(desc)

            # Try client method, fallback to manual
            try:
                if hasattr(client, "download_snapshot"):
                    client.download_snapshot(
                        collection_name=collection_name,
                        snapshot_name=snap_name,
                        out=out_path
                    )
                else:
                    raise AttributeError("download_snapshot missing")
            except (AttributeError, TypeError):
                logger.warning("[Snapshot] client.download_snapshot missing or failed. Trying manual download.")
                _manual_download_snapshot(client, collection_name, snap_name, out_path)

        logger.info(f"[Snapshot] Downloaded: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"[Snapshot] Create failed: {e}")
        raise

def restore_snapshot(path: str):
    try:
        if not _is_under_snapshot_dir(path):
            raise ValueError("Snapshot path must be under SNAPSHOT_DIR")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Snapshot not found: {path}")

        filename = os.path.basename(path)
        collection_name = filename.split("_")[0]

        with acquire_manager() as mgr:
            client: QdrantClient = mgr.client
            logger.info(f"[Snapshot] Recovering '{collection_name}' from {path}")
            # Local file must be uploaded to server
            _manual_upload_snapshot(client, collection_name, path)

        logger.info(f"[Snapshot] Recovered: {collection_name}")
    except Exception as e:
        logger.error(f"[Snapshot] Restore failed: {e}")
        raise

def list_snapshots() -> list[str]:
    _ensure_snapshot_dir()
    return sorted(
        [os.path.join(SNAPSHOT_DIR, f) for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".snapshot")],
        key=os.path.getmtime,
        reverse=True,
    )

def delete_snapshot(path: str) -> bool:
    try:
        if not _is_under_snapshot_dir(path):
            logger.warning(f"[Snapshot] Reject delete outside SNAPSHOT_DIR: {path}")
            return False
        if not os.path.exists(path):
            logger.warning(f"[Snapshot] File not found: {path}")
            return False
        os.remove(path)
        logger.info(f"[Snapshot] Deleted: {path}")
        return True
    except Exception as e:
        logger.error(f"[Snapshot] Delete failed: {e}")
        return False