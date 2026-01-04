from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    PointStruct,
    Filter,
    PointIdsList,
    FilterSelector,
    NamedVector,
    SparseVector,
)
import numpy as np
import json
import os
from typing import Optional
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.utils.id_helper import make_doc_hash_id_from_json, generate_point_id

from .embedding import content_embedder, model as dense_model
from .config import FORMATS
from .sparse_engine import splade_encode
from .sparse_engine import bm25_encode


# ==========================================================
# (1) 개별 문서 업서트
# ==========================================================


def filter_core_sentences(text: str, top_p: float = 0.2, min_sentences: int = 3) -> str:
    """
    ParetoRAG implementation: Selects top P% of sentences based on importance tokens/weights.
    For simplicity, we use sentence length and keyword density (BM25-like) here.
    """
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= min_sentences:
        return text

    # Calculate simple importance score (sentence length + word diversity)
    scores = []
    for s in sentences:
        words = s.split()
        if not words:
            scores.append(0)
            continue
        score = len(s) * len(set(words)) / len(words)
        scores.append(score)

    # Select top P
    k = max(min_sentences, int(len(sentences) * top_p))
    top_indices = np.argsort(scores)[-k:]
    # Maintain original order
    top_indices.sort()

    return " ".join([sentences[i] for i in top_indices])


def create_doc_upsert(client, col_name, data, dense_model=None):
    """
    Enhanced Phase 5 Upsert:
    - Multi-Vector: title_dense, body_dense, sparse, splade
    - ParetoRAG: Filter core sentences for the 'body_dense' vector
    """
    try:
        trace(f"Upserting document into {col_name} (Phase 5)")

        if not data:
            logger.warning(f"[Upsert] Empty data skipped for collection {col_name}")
            return

        raw_text = data.get("content") or data.get("contents") or ""
        title = data.get("title", "")
        if not raw_text.strip():
            logger.warning(f"[Upsert] Empty content skipped in {col_name}")
            return

        db_id = make_doc_hash_id_from_json(data)
        data["db_id"] = db_id

        if dense_model is None:
            from .vector_db_manager import VectorDBManager
            dense_model = VectorDBManager().dense_model

        # Multi-Tenancy Defaults
        tenant_id = data.get("tenant_id", "public")
        access_level = data.get("access_level", 1)

        # --- Multi-Vector Encoding ---
        # 1. Title Vector (Specific intent)
        title_vec = (
            dense_model.encode(title).tolist() if title else [0.0] * 384
        )  # Fallback

        # 2. Pareto Body Vector (Core essence)
        core_text = filter_core_sentences(raw_text)
        body_vec = dense_model.encode(core_text).tolist()

        # 3. Sparse & SPLADE (Full context)
        bm25_dict = bm25_encode(raw_text)
        splade_dict = splade_encode(raw_text)

        sparse_vec = SparseVector(
            indices=[int(k) for k in bm25_dict.keys()],
            values=[float(v) for v in bm25_dict.values()],
        )
        splade_vec = SparseVector(
            indices=[int(k) for k in splade_dict.keys()],
            values=[float(v) for v in splade_dict.values()],
        )

        chunks = content_embedder(raw_text)
        if not chunks:
            logger.warning(f"[Upsert] No chunks generated for db_id={db_id}")
            return

        points = []

        # --- (A) Parent Record: Stores full text context ---
        parent_payload = {
            "db_id": db_id,
            "id": data.get("id"),
            "full_text": raw_text,
            "title": title,
            "is_parent": True,
            "is_child": False,
            "tenant_id": tenant_id,
            "access_level": access_level,
        }
        # Copy other metadata
        for key in ["department", "category", "year"]:
            if key in data:
                parent_payload[key] = data[key]
        # Parent record uses a unique point ID based on db_id alone (or with -parent suffix)
        parent_point = PointStruct(
            id=generate_point_id(db_id, -1),  # -1 index for parent
            vector={
                "dense": body_vec,  # Use Pareto filtered core as parent vector
                "title": title_vec,
                "sparse": sparse_vec,
                "splade": splade_vec,
            },
            payload=parent_payload,
        )
        points.append(parent_point)

        # --- (B) Child Records: Semantic chunks ---
        for i, (chunk_text, _) in enumerate(chunks):
            # Phase 7 Refinement: LGMGC-lite Contextual Anchors
            # Prepend title to each chunk to ensure semantic boundary preservation
            anchored_text = f"[{title}] {chunk_text}"

            payload = {
                "db_id": db_id,
                "id": data.get("id"),
                "text": anchored_text,
                "title": title,
                "is_pareto": True if i == 0 else False,
                "is_parent": False,
                "is_child": True,
            }

            # Unified metadata preservation for Phase 7
            payload["tenant_id"] = tenant_id
            payload["access_level"] = access_level
            for key in ["department", "category", "year"]:
                if key in data and key not in payload:
                    payload[key] = data[key]

            if col_name in FORMATS:
                for key in FORMATS[col_name]:
                    if key not in payload:
                        payload[key] = data.get(key, "")

            point_id = generate_point_id(db_id, i)

            # --- Qdrant Phase 5 Named Vectors ---
            vectors = {
                "dense": body_vec
                if i == 0
                else dense_model.encode(chunk_text).tolist(),
                "title": title_vec,
                "sparse": sparse_vec,
                "splade": splade_vec,
            }

            point = PointStruct(id=point_id, vector=vectors, payload=payload)
            points.append(point)

        if points:
            client.upsert(collection_name=col_name, points=points)
            logger.info(
                f"[Upsert] {col_name}: db_id={db_id[:12]}... (Phase 7: Parent-Child) inserted."
            )
        else:
            logger.warning(f"[Upsert] No points created for db_id={db_id}")

    except Exception as e:
        logger.error(f"[Upsert] Error for {col_name}: {e}")
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
            collection_name=col_name, ids=[db_id], with_payload=True, with_vectors=True
        )
        if not response:
            logger.warning(f"[Read] Document not found: {db_id} in {col_name}")
            return None
        logger.debug(
            f"[Read] Retrieved 1 document (db_id={db_id[:12]}...) from {col_name}"
        )
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
            values=[float(v) for v in bm25_dict.values()],
        )
        splade_vec = SparseVector(
            indices=[int(k) for k in splade_dict.keys()],
            values=[float(v) for v in splade_dict.values()],
        )

        # payload 생성
        points = []
        for i, (chunk_text, _) in enumerate(chunks):
            payload = {**updated_data, "db_id": db_id, "text": chunk_text}
            point = PointStruct(
                id=f"{db_id}-{i}",
                vector={"dense": dense_vec, "sparse": sparse_vec, "splade": splade_vec},
                payload=payload,
            )
            points.append(point)

        # 업서트 실행
        if points:
            client.upsert(collection_name=col_name, points=points)
            logger.info(
                f"[Update] Updated {len(points)} chunks for db_id={db_id[:12]}... in {col_name}"
            )
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
        client.delete(
            collection_name=col_name, points_selector=PointIdsList(points=[db_id])
        )
        logger.info(f"[Delete] Deleted db_id={db_id[:12]}... from {col_name}")
    except Exception as e:
        logger.error(f"[Delete] Error deleting db_id={db_id} from {col_name}: {e}")


def initialize_col(client, col_name):
    """
    컬렉션 전체 초기화 (모든 포인트 삭제)
    """
    trace(f"Initializing collection {col_name}")
    try:
        client.delete(
            collection_name=col_name,
            points_selector=FilterSelector(filter=Filter(must=[])),
        )
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

                logger.debug(
                    f"[UpsertFolder] Uploading {i + 1}/{len(json_files)}: {filename} [db_id={db_id[:12]}...]"
                )

                # 통일된 업서트 함수 호출 (내부적으로 동일 ID 규칙 유지)
                create_doc_upsert(client, col_name, data, dense_model=dense_model)
                success += 1

            except json.JSONDecodeError as e:
                logger.warning(f"[UpsertFolder] JSON decode error in {filename}: {e}")
                fail += 1
            except Exception as e:
                logger.error(f"[UpsertFolder] Error processing {filename}: {e}")
                fail += 1

        logger.info(
            f"[UpsertFolder] Summary for {col_name}: {success} succeeded, {fail} failed"
        )

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
    query_filter: Optional[Filter] = None,
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
            # Phase 7: Exclude Parent records from main search
            exclude_parent = models.FieldCondition(
                key="is_parent", match=models.MatchValue(value=True)
            )

            # Create a fresh filter to avoid side effects on the passed object
            final_chk = None
            if query_filter:
                # Clone must/must_not to avoid mutation
                must_conds = list(query_filter.must) if query_filter.must else []
                must_not_conds = (
                    list(query_filter.must_not) if query_filter.must_not else []
                )
                should_conds = list(query_filter.should) if query_filter.should else []

                # Add exclusion if not present
                if exclude_parent not in must_not_conds:
                    must_not_conds.append(exclude_parent)

                final_chk = models.Filter(
                    must=must_conds, must_not=must_not_conds, should=should_conds
                )
            else:
                final_chk = models.Filter(must_not=[exclude_parent])

            # Determine search method based on Qdrant version compatibility
            # v1.7.x does not support query_points (Universal Query). Use search() for vectors.
            points = []

            # Check if query is a vector type (List, Tuple, Numpy, SparseVector, NamedVector)
            is_vector = isinstance(
                query, (list, tuple, models.SparseVector, models.NamedVector)
            ) or hasattr(query, "tolist")
            # logger.info(f"[DEBUG QueryUnique] is_vector={is_vector} type={type(query)} using={using}")

            if is_vector:
                try:
                    import requests

                    base_url = client._client.rest_uri
                    api_key = client._client._api_key

                    headers = {"Content-Type": "application/json"}
                    if api_key:
                        headers["api-key"] = api_key

                    vector_param = query
                    if isinstance(query, (models.SparseVector, models.NamedVector)):
                        if hasattr(query, "dict"):
                            vector_param = query.dict(exclude_none=True)
                        else:
                            vector_param = query.model_dump(exclude_none=True)
                    elif hasattr(query, "tolist"):
                        vector_param = query.tolist()

                    if using:
                        vector_param = {"name": using, "vector": vector_param}

                    filter_param = None
                    if final_chk:
                        if hasattr(final_chk, "dict"):
                            filter_param = final_chk.dict(exclude_none=True)
                        else:
                            filter_param = final_chk.model_dump(exclude_none=True)

                    payload = {
                        "vector": vector_param,
                        "filter": filter_param,
                        "limit": limit,
                        "offset": offset,
                        "with_payload": True,
                        "with_vector": False,
                    }

                    url = f"{base_url}/collections/{collection_name}/points/search"
                    resp = requests.post(
                        url, json=payload, headers=headers, timeout=10.0
                    )

                    if not resp.ok:
                        logger.error(
                            f"[QueryUnique] Legacy Search Failed: {resp.status_code} | {resp.text}"
                        )
                    resp.raise_for_status()

                    res_json = resp.json()
                    points = []
                    for item in res_json.get("result", []):
                        points.append(
                            models.ScoredPoint(
                                id=item.get("id"),
                                version=item.get("version"),
                                score=item.get("score"),
                                payload=item.get("payload"),
                                vector=item.get("vector"),
                            )
                        )

                    logger.info(
                        f"[QueryUnique] Legacy API '{using}' found {len(points)} docs"
                    )

                except Exception as e:
                    logger.error(f"[QueryUnique] Raw HTTP Search Failed: {e}")
                    points = []
            else:
                # logger.info(f"[DEBUG QueryUnique] Using scroll fallback for {type(query)}")
                # ... existing code ...
                # Filter/Scroll (Fallback logic if query isn't a vector)
                # Note: scroll doesn't support integer offset efficiently in loop like this
                # But if we must support it:
                result_tuple = client.scroll(
                    collection_name=collection_name,
                    scroll_filter=final_chk,
                    limit=limit,
                    with_payload=True,
                    # offset=... scroll takes ID, not int.
                    # For legacy scroll loop, we'd need to track last_id.
                    # Assuming non-vector usage isn't the primary path here.
                )
                points = result_tuple[0]

            if not points:
                break

            # DEBUG: Log the filter used (once per call)
            if offset == 0:
                logger.info(f"[DEBUG QueryUnique] Filter: {final_chk}")

            for r in points:
                # Qdrant의 반환 구조가 tuple(r.id, r.payload) 형태일 수도 있어서 안전 처리
                point = r[1] if isinstance(r, tuple) else r
                payload = getattr(point, "payload", {}) or {}

                # DEBUG: Log one payload to verify access_level
                if offset == 0 and len(seen_docs) == 0:
                    logger.info(
                        f"[DEBUG Payload] ID={getattr(point, 'id', 'N/A')} Access={payload.get('access_level')} Tenant={payload.get('tenant_id')}"
                    )

                # db_id 우선 사용 (없으면 id/parent_id fallback)
                # parent_id or id 우선 사용 (청크/버전 중복 제거)
                unified_id = (
                    payload.get("parent_id")
                    or payload.get("id")
                    or payload.get("db_id")
                    or getattr(point, "id", None)
                )

                if not unified_id:
                    logger.warning(
                        "[QueryUnique] Point without valid ID encountered — skipping."
                    )
                    continue

                if unified_id not in seen_docs:
                    seen_docs.add(unified_id)
                    unique_results.append(r)

                if len(unique_results) >= top_k:
                    break

            offset += step
            limit += step

        logger.debug(
            f"[QueryUnique] Retrieved {len(unique_results)} unique docs from {collection_name}"
        )
        return unique_results

    except Exception as e:
        err_msg = str(e)
        if "Not existing vector name" in err_msg:
            logger.warning(
                f"[QueryUnique] Collection '{collection_name}' does not support vector '{using}'. Skipping."
            )
        elif "400" in err_msg and "Wrong input" in err_msg:
            logger.warning(
                f"[QueryUnique] Bad Request in '{collection_name}' for '{using}': {err_msg}"
            )
        else:
            logger.error(f"[QueryUnique] Error in {collection_name}: {e}")
        return unique_results
