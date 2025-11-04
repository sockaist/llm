import hashlib
import os
import json

def make_hash_id(source: str) -> str:
    """주어진 문자열(source)을 기반으로 고정 해시 ID 생성."""
    if not source:
        raise ValueError("make_hash_id() requires a non-empty source string.")
    return hashlib.md5(source.encode("utf-8")).hexdigest()


def make_hash_id_from_path(path: str, base_dir: str = ".") -> str:
    """파일 경로를 기반으로 해시 ID 생성 (상대경로 기준)."""
    try:
        rel_path = os.path.relpath(path, start=base_dir)
    except Exception:
        rel_path = path  # fallback
    return hashlib.md5(rel_path.encode("utf-8")).hexdigest()


def make_doc_hash_id_from_json(data: dict) -> str:
    """문서 전체 JSON을 문자열로 직렬화하고 SHA-256 해시 생성"""
    normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()