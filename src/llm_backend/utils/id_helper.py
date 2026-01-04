import hashlib
import os
import json
import uuid


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


# 프로젝트 전용 네임스페이스 (고정 UUID)
# 임의로 생성된 UUID를 고정값으로 사용
NAMESPACE_SOCKAIST = uuid.UUID("5fffda67-50f4-46b3-ad71-4bb25160ad55")


def generate_point_id(db_id: str, chunk_index: int = 0) -> str:
    """
    db_id(해시)와 chunk_index를 결합하여 결정론적 UUID 생성.

    Args:
        db_id (str): 문서의 고유 해시 ID
        chunk_index (int): 청크 인덱스 (기본값 0)

    Returns:
        str: Qdrant Point ID (UUID 형식 문자열)
    """
    # db_id와 chunk_index를 결합하여 시드 생성
    seed = f"{db_id}_{chunk_index}"
    return str(uuid.uuid5(NAMESPACE_SOCKAIST, seed))
