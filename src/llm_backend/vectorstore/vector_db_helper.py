from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue,
    PointIdsList, FilterSelector, SearchRequest, SearchParams, NamedVector, SparseVector
)
from qdrant_client.http.models import ScoredPoint
import numpy as np
import json
import os
import uuid
from typing import List, Dict, Any
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.utils.id_helper import make_doc_hash_id_from_json, generate_point_id

from .embedding import content_embedder, model as dense_model
from .config import FORMATS
from .splade_module import splade_encode
from .sparse_helper import bm25_encode


# ==========================================================
# (1) 개별 문서 업서트
# ==========================================================

def create_doc_upsert(client, col_name, data, dense_model=None):
    """
    Create and upsert a document into Qdrant with
    Dense (SentenceTransformer), Sparse (BM25), and SPLADE vectors.
    Uses JSON 전체 해시(SHA-256) 기반 db_id for deterministic consistency.
    """
    try:
        trace(f"Upserting document into {col_name}")

        if not data:
            logger.warning(f"[Upsert] Empty data skipped for collection {col_name}")
            return

        raw_text = data.get("content") or data.get("contents") or ""
        if not raw_text.strip():
            logger.warning(f"[Upsert] Empty content skipped in {col_name}")
            return

        # JSON 전체를 직렬화 후 SHA-256 해시 생성
        db_id = make_doc_hash_id_from_json(data)
        data["db_id"] = db_id  # payload에도 포함

        # 중복 방지 체크 제거 (Upsert 덮어쓰기 허용)
        # Deterministic ID를 사용하므로 동일 컨텐츠는 동일 ID를 가져 자동 갱신됩니다.


        if dense_model is None:
            raise ValueError("Dense model not loaded. Please pass dense_model parameter.")

        # 벡터 생성
        dense_vec = dense_model.encode(raw_text)
        if isinstance(dense_vec, np.ndarray):
            dense_vec = dense_vec.tolist()
        dense_vec = [float(x) for x in dense_vec]

        bm25_dict = bm25_encode(raw_text)
        splade_dict = splade_encode(raw_text)

        sparse_vec = SparseVector(
            indices=[int(k) for k in bm25_dict.keys()],
            values=[float(v) for v in bm25_dict.values()]
        )
        splade_vec = SparseVector(
            indices=[int(k) for k in splade_dict.keys()],
            values=[float(v) for v in splade_dict.values()]
        )

        chunks = content_embedder(raw_text)
        if not chunks:
            logger.warning(f"[Upsert] No chunks generated for db_id={db_id}")
            return

        # payload 생성
        points = []
        for i, (chunk_text, _) in enumerate(chunks):
            payload = {
                "db_id": db_id,                  # SHA-256 해시 기반 고유 ID
                "id": data.get("id"),            # 원본 id (보존용)
                "parent_id": data.get("id"),     # legacy 호환
                "text": chunk_text,
                "title": data.get("title", "")
            }

            # FORMATS 스키마에 맞는 필드 복사
            if col_name in FORMATS:
                for key in FORMATS[col_name]:
                    payload[key] = data.get(key, "")

            # Qdrant에 저장할 Point ID는 UUID 형식으로 (Deterministic)
            point_id = generate_point_id(db_id, i)


            point = PointStruct(
                id=point_id,  # 이제 Qdrant가 완전히 허용하는 형식
                vector={
                    "dense": dense_vec,
                    "sparse": sparse_vec,
                    "splade": splade_vec
                },
                payload=payload
            )
            points.append(point)

        # 업서트 실행
        if points:
            client.upsert(collection_name=col_name, points=points)
            logger.info(f"[Upsert] {col_name}: db_id={db_id[:12]}... ({len(points)} chunks) inserted successfully.")
        else:
            logger.warning(f"[Upsert] No points created for db_id={db_id}")

    except Exception as e:
        logger.error(f"[Upsert] Error for {col_name}: {e} | db_id={data.get('db_id')}")
        raise


## ==========================================================
# (2) 단일 문서 조회
# ==========================================================
def read_doc(client, col_name, db_id):
    """
    db_id (SHA-256 해시 기반)로 단일 문서를 조회.
    """
    trace(f"Reading document db_id={db_id[:12]}... from {col_name}")
    try:
        response = client.retrieve(
            collection_name=col_name,
            ids=[db_id],
            with_payload=True,
            with_vectors=True
        )
        if not response:
            logger.warning(f"[Read] Document not found: {db_id} in {col_name}")
            return None
        logger.debug(f"[Read] Retrieved 1 document (db_id={db_id[:12]}...) from {col_name}")
        return response[0]
    except Exception as e:
        logger.error(f"[Read] Error reading db_id={db_id} from {col_name}: {e}")
        return None


# ==========================================================
# (3) 문서 업데이트
# ==========================================================
def update_doc(client, col_name, db_id, updated_data):
    """
    기존 문서의 payload와 vector를 업데이트.
    항상 db_id 기반으로 수행.
    """
    try:
        trace(f"Updating document db_id={db_id[:12]}... in {col_name}")

        if not updated_data:
            logger.warning(f"[Update] Empty data for db_id {db_id}")
            return

        raw_text = updated_data.get("content") or updated_data.get("contents") or ""
        if not raw_text.strip():
            logger.warning(f"[Update] Empty content for db_id {db_id}")
            return

        # 새 chunk 생성
        chunks = content_embedder(raw_text)
        if not chunks:
            logger.warning(f"[Update] No chunks generated for db_id={db_id}")
            return

        # 새 벡터 계산
        dense_vec = dense_model.encode(raw_text)
        if isinstance(dense_vec, np.ndarray):
            dense_vec = dense_vec.tolist()
        dense_vec = [float(x) for x in dense_vec]

        bm25_dict = bm25_encode(raw_text)
        splade_dict = splade_encode(raw_text)
        sparse_vec = SparseVector(
            indices=[int(k) for k in bm25_dict.keys()],
            values=[float(v) for v in bm25_dict.values()]
        )
        splade_vec = SparseVector(
            indices=[int(k) for k in splade_dict.keys()],
            values=[float(v) for v in splade_dict.values()]
        )

        # payload 생성
        points = []
        for i, (chunk_text, _) in enumerate(chunks):
            payload = {
                **updated_data,
                "db_id": db_id,
                "text": chunk_text
            }
            point = PointStruct(
                id=f"{db_id}-{i}",
                vector={
                    "dense": dense_vec,
                    "sparse": sparse_vec,
                    "splade": splade_vec
                },
                payload=payload
            )
            points.append(point)

        # 업서트 실행
        if points:
            client.upsert(collection_name=col_name, points=points)
            logger.info(f"[Update] Updated {len(points)} chunks for db_id={db_id[:12]}... in {col_name}")
        else:
            logger.warning(f"[Update] No points to update for db_id={db_id}")

    except Exception as e:
        logger.error(f"[Update] Error updating db_id={db_id} in {col_name}: {e}")
        raise


# ==========================================================
# (4) 문서 삭제 및 초기화
# ==========================================================
def delete_doc(client, col_name, db_id):
    """
    db_id 기반으로 문서 삭제.
    """
    trace(f"Deleting document db_id={db_id[:12]}... from {col_name}")
    try:
        client.delete(collection_name=col_name, points_selector=PointIdsList(points=[db_id]))
        logger.info(f"[Delete] Deleted db_id={db_id[:12]}... from {col_name}")
    except Exception as e:
        logger.error(f"[Delete] Error deleting db_id={db_id} from {col_name}: {e}")


def initialize_col(client, col_name):
    """
    컬렉션 전체 초기화 (모든 포인트 삭제)
    """
    trace(f"Initializing collection {col_name}")
    try:
        client.delete(collection_name=col_name, points_selector=FilterSelector(filter=Filter(must=[])))
        logger.info(f"[Init] Cleared all points in {col_name}")
    except Exception as e:
        logger.error(f"[Init] Error clearing {col_name}: {e}")


# ==========================================================
# (5) 검색 및 질의
# ==========================================================
def search_doc(client, query, col_name, k):
    trace(f"Searching in {col_name} with query='{query}' (top {k})")
    query_vector = dense_model.encode(query)
    results = client.search(
        collection_name=col_name,
        query_vector=NamedVector(name="dense", vector=query_vector),
        limit=k,
    )
    logger.debug(f"[Search] Retrieved {len(results)} results from {col_name}")
    return results


# ==========================================================
# (6) 폴더 업서트
# ==========================================================
# ==========================================================
# (6) 폴더 업서트
# ==========================================================
import os
import json
from qdrant_client import models
from llm_backend.utils.logger import logger
from llm_backend.utils.id_helper import make_doc_hash_id_from_json
from llm_backend.vectorstore.vector_db_helper import create_doc_upsert


def upsert_folder(client, folder_path, col_name, n=0, dense_model=None):
    """
    폴더 내 JSON 파일들을 일괄 업로드.
    모든 문서에 대해 make_doc_hash_id_from_json()을 사용하여 db_id를 생성하고,
       create_doc_upsert()를 호출해 일관된 해시 기반 ID를 보장한다.
    """
    try:
        trace(f"Upserting folder {folder_path} → {col_name}")

        if not os.path.exists(folder_path):
            logger.error(f"[UpsertFolder] Folder not found: {folder_path}")
            return

        json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
        if not json_files:
            logger.warning(f"[UpsertFolder] No JSON files in {folder_path}")
            return

        logger.info(f"[UpsertFolder] Found {len(json_files)} files in {folder_path}")
        success, fail = 0, 0

        # 필드 인덱스 보장 (id/db_id 모두 사용)
        try:
            client.create_payload_index(
                collection_name=col_name,
                field_name="db_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
                wait=True,
            )
        except Exception:
            pass  # 이미 존재 시 무시

        for i, filename in enumerate(json_files):
            if n and i >= n:
                break
            file_path = os.path.join(folder_path, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # JSON 전체 해시 기반 db_id 생성
                db_id = make_doc_hash_id_from_json(data)
                data["db_id"] = db_id  # payload에도 저장

                logger.debug(f"[UpsertFolder] Uploading {i+1}/{len(json_files)}: {filename} [db_id={db_id[:12]}...]")

                # 통일된 업서트 함수 호출 (내부적으로 동일 ID 규칙 유지)
                create_doc_upsert(client, col_name, data, dense_model=dense_model)
                success += 1

            except json.JSONDecodeError as e:
                logger.warning(f"[UpsertFolder] JSON decode error in {filename}: {e}")
                fail += 1
            except Exception as e:
                logger.error(f"[UpsertFolder] Error processing {filename}: {e}")
                fail += 1

        logger.info(f"[UpsertFolder] Summary for {col_name}: {success} succeeded, {fail} failed")

    except Exception as e:
        logger.error(f"[UpsertFolder] Error in folder {folder_path}: {e}")
        raise

# ==========================================================
# (7) 중복 제거 검색 (db_id 기반)
# ==========================================================
def query_unique_docs(
    client: QdrantClient,
    collection_name: str,
    query,
    using: str,
    top_k: int = 5,
    step: int = 50,
    max_limit: int = 1000,
):
    """
    Qdrant에서 중복 없는 문서를 검색합니다.
    각 문서는 JSON 전체 해시 기반의 db_id를 기준으로 유일하게 식별됩니다.
    """
    trace(f"Querying unique docs from {collection_name} (top_k={top_k})")

    seen_docs = set()
    unique_results = []
    offset = 0
    limit = step

    try:
        while len(unique_results) < top_k and limit <= max_limit:
            results = client.query_points(
                collection_name=collection_name,
                query=query,
                using=using,
                limit=limit,
                offset=offset,
            )

            points = results.points if hasattr(results, "points") else results
            if not points:
                break

            for r in points:
                # Qdrant의 반환 구조가 tuple(r.id, r.payload) 형태일 수도 있어서 안전 처리
                point = r[1] if isinstance(r, tuple) else r
                payload = getattr(point, "payload", {}) or {}

                # db_id 우선 사용 (없으면 id/parent_id fallback)
                db_id = (
                    payload.get("db_id")
                    or payload.get("id")
                    or payload.get("parent_id")
                    or getattr(point, "id", None)
                )

                if not db_id:
                    logger.warning("[QueryUnique] Point without valid ID encountered — skipping.")
                    continue

                if db_id not in seen_docs:
                    seen_docs.add(db_id)
                    unique_results.append(r)

                if len(unique_results) >= top_k:
                    break

            offset += step
            limit += step

        logger.debug(f"[QueryUnique] Retrieved {len(unique_results)} unique docs from {collection_name}")
        return unique_results

    except Exception as e:
        logger.error(f"[QueryUnique] Error in {collection_name}: {e}")
        return unique_results