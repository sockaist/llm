"""Ingestion and payload operations for Qdrant via VectorDBManager."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from qdrant_client import models
from qdrant_client.models import SparseVector

from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.utils.id_helper import make_hash_id_from_path, make_doc_hash_id_from_json, generate_point_id

from llm_backend.vectorstore.sparse_helper import bm25_encode
from llm_backend.vectorstore.splade_module import splade_encode


def make_doc_hash_id(path: str) -> str:
    return make_hash_id_from_path(path)


def upsert_folder(manager, folder: str, collection: str, batch_size: int = 50) -> None:
    trace(f"upsert_folder({folder}, {collection}, batch_size={batch_size})")

    if not os.path.exists(folder):
        logger.warning(f"Folder not found: {folder}")
        return

    files = [f for f in os.listdir(folder) if f.endswith(".json")]
    total = len(files)
    if total == 0:
        logger.warning(f"No JSON files found in {folder}")
        return

    logger.info(f"Upserting {total} JSON files into '{collection}' (Batch Size: {batch_size})")

    batch_data = []
    success_count = 0
    fail_count = 0

    def _process_batch(docs: List[Dict[str, Any]]) -> int:
        nonlocal success_count, fail_count, idx
        if not docs:
            return 0
        
        try:
            texts = []
            valid_docs = []
            
            # Filter and Extract Texts
            for d in docs:
                content = d.get("content") or d.get("contents") or ""
                if isinstance(content, str) and content.strip():
                    texts.append(content)
                    valid_docs.append(d)
                else:
                    logger.warning(f"[Upsert] Skipping doc with empty content (id={d.get('id', 'unknown')})")
            
            if not texts:
                return 0

            # --- Batch Encoding ---
            # 1. Dense
            dense_vecs = manager.dense_model.encode(texts) # Returns list of numpy arrays or tensor

            # 2. Sparse (BM25)
            bm25_vecs_list = bm25_encode(texts) # Returns list of dicts

            # 3. SPLADE
            try:
                splade_vecs_list = splade_encode(texts) # Returns list of dicts
            except Exception as e:
                logger.error(f"[SPLADE] Batch encoding failed: {e}. Fallback to empty.")
                # Fallback: empty vectors for all
                splade_vecs_list = [{} for _ in texts]

            # --- Create Points ---
            points = []
            for i, doc in enumerate(valid_docs):
                db_id = make_doc_hash_id_from_json(doc)
                doc["db_id"] = db_id
                
                point_id = generate_point_id(db_id)
                
                # BM25 Vector
                b_vec = bm25_vecs_list[i]
                bm25_sv = models.SparseVector(indices=list(b_vec.keys()), values=list(b_vec.values()))

                # SPLADE Vector
                s_vec = splade_vecs_list[i]
                splade_sv = models.SparseVector(indices=list(s_vec.keys()), values=list(s_vec.values()))

                payload = {
                    **doc,
                    "id": doc.get("id", db_id),
                    "parent_id": doc.get("id", db_id),
                    "db_id": db_id,
                }

                payload = {
                    **doc,
                    "id": doc.get("id", db_id),
                    "parent_id": doc.get("id", db_id),
                    "db_id": db_id,
                    # Multi-Tenancy Defaults
                    "tenant_id": doc.get("tenant_id", "public"),
                    "access_level": doc.get("access_level", 1)
                }

                point = models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vecs[i].tolist(),
                        "sparse": bm25_sv, 
                        "splade": splade_sv
                    },
                    payload=payload,
                )
                points.append(point)

            # --- Upsert ---
            if points:
                manager.client.upsert(collection_name=collection, points=points)
                count = len(points)
                logger.info(f"[{collection}] Flushed batch (Processed {count} docs)...")
                return count
            return 0

        except Exception as e:
            logger.error(f"[Upsert] Batch processing failed: {e}")
            fail_count += len(docs)
            return 0

    for idx, f in enumerate(files, 1):
        try:
            file_path = os.path.join(folder, f)
            with open(file_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            
            batch_data.append(data)
            
            if len(batch_data) >= batch_size:
                succeeded = _process_batch(batch_data)
                success_count += succeeded
                batch_data = []

        except Exception as exc:  # noqa: BLE001
            fail_count += 1
            logger.error(f"[Upsert Fail] File read error {f}: {exc}")

    # Final Flush
    if batch_data:
        succeeded = _process_batch(batch_data)
        success_count += succeeded
    
    logger.info(f"Finished upserting '{collection}' — {success_count} succeeded, {fail_count} failed (read/batch errors).")


def upsert_document(manager, col: str, data: dict, doc_id: Optional[str] = None) -> None:
    """Upsert a single document with dense + BM25 + SPLADE vectors."""

    trace(f"upsert_document({col}, id={doc_id})")

    try:
        if not col:
            logger.error("[Upsert] Collection name is required")
            return
        if not isinstance(data, dict):
            logger.error("[Upsert] Data must be a dict")
            return

        # 컬렉션 존재 확인
        try:
            manager.client.get_collection(collection_name=col)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[Upsert] Collection '{col}' not found: {exc}")
            return

        content = data.get("content") or data.get("contents") or ""
        if not isinstance(content, str) or not content.strip():
            logger.warning(f"[Upsert] Skip doc without content in '{col}' (id={doc_id})")
            return

        json.dumps(data, sort_keys=True, ensure_ascii=False)
        db_id = make_doc_hash_id_from_json(data)
        data["db_id"] = db_id

        dense_vec = manager.dense_model.encode(content)
        bm25_vec = bm25_encode(content)
        bm25_sv = SparseVector(indices=list(bm25_vec.keys()), values=list(bm25_vec.values()))

        # SPLADE는 실패해도 업서트를 계속 진행 (dense+BM25만 저장)
        try:
            splade_vec = splade_encode(content)
            splade_sv = SparseVector(indices=list(splade_vec.keys()), values=list(splade_vec.values()))
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[Upsert] SPLADE encoding failed; storing dense+BM25 only: {exc}")
            splade_sv = SparseVector(indices=[], values=[])

        # Multi-Tenancy & Encryption
        tenant_id = data.get("tenant_id", "public")
        access_level = data.get("access_level", 1)
        
        # Determine if encryption is required (Private tenant OR explicit flag)
        should_encrypt = data.get("encrypt_content", False) or (tenant_id != "public")
        
        stored_content = content
        is_encrypted = False
        
        if should_encrypt:
            try:
                from llm_backend.security.encryption_manager import EncryptionManager
                encryptor = EncryptionManager.get_instance()
                stored_content = encryptor.encrypt_text(tenant_id, content)
                is_encrypted = True
            except Exception as e:
                logger.error(f"[Upsert] Encryption failed for {doc_id} (tenant={tenant_id}): {e}")
                # Fallback: Do NOT store plaintext if encryption was intended?
                # For safety, let's fail the upsert or store a placeholder.
                # Storing plaintext when encryption failed is a security risk.
                return

        payload = {
            **data,
            "id": data.get("id", doc_id),
            "parent_id": data.get("id", doc_id),
            "db_id": db_id,
            "tenant_id": tenant_id,
            "access_level": access_level,
            "content": stored_content,
            "content_encrypted": is_encrypted
        }

        point_id = generate_point_id(db_id)


        manager.client.upsert(
            collection_name=col,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector={"dense": dense_vec, "sparse": bm25_sv, "splade": splade_sv},
                    payload=payload,
                )
            ],
        )

        logger.info(f"[Upsert] {col}: db_id={db_id[:12]} inserted successfully")

    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Upsert Error] db_id={db_id[:12]} in {col}: {exc}")


def update_payload(manager, col: str, doc_id: str, new_payload: dict, merge: bool = True) -> bool:
    trace(f"update_payload({col}, id={doc_id}, merge={merge})")
    try:
        result = manager.client.retrieve(collection_name=col, ids=[doc_id], with_payload=True)
        if not result:
            logger.warning(f"[UpdatePayload] Document not found in {col}: id={doc_id}")
            return False

        old_payload = result[0].payload or {}
        updated_payload = {**old_payload, **new_payload} if merge else new_payload

        manager.client.set_payload(collection_name=col, payload=updated_payload, points=[doc_id])
        logger.info(f"[UpdatePayload] Updated payload for doc_id={doc_id} in '{col}'")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[UpdatePayload] Error updating payload for id={doc_id}: {exc}")
        return False


def delete_document(manager, col: str, db_id: str) -> bool:
    trace(f"delete_document({col}, db_id={db_id[:12]}...)")
    try:
        # CRITICAL FIX: The point is stored under a deterministic UUID derived from db_id.
        # We must use the same UUID to delete it.
        # db_id is the string hash, point_id is the UUID.
        point_id = generate_point_id(db_id)
        
        manager.client.delete(
            collection_name=col,
            points_selector=models.PointIdsList(points=[point_id]),
        )
        logger.info(f"[Delete] Deleted db_id={db_id[:12]}...(UUID={point_id}) from '{col}'")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Delete] Error deleting db_id={db_id[:12]}... from '{col}': {exc}")
        return False


def delete_by_filter(manager, col: str, field: str, value: Any) -> int:
    trace(f"delete_by_filter({col}, field={field}, value={value})")
    try:
        condition = models.Filter(must=[models.FieldCondition(key=field, match=models.MatchValue(value=value))])
        result = manager.client.delete(
            collection_name=col,
            points_selector=condition,
        )
        deleted_count = getattr(result, "result", {}).get("num_points", 0)
        logger.info(f"[DeleteByFilter] Deleted {deleted_count} docs from '{col}' where {field}={value}")
        return deleted_count
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[DeleteByFilter] Error deleting docs from {col}: {exc}")
        return 0


def filter_search(
    manager,
    col: str,
    filters: Dict[str, Any],
    limit: int = 10,
    with_vectors: bool = False,
) -> List[Dict[str, Any]]:
    trace(f"filter_search({col}, filters={filters})")
    try:
        must_conditions = [models.FieldCondition(key=k, match=models.MatchValue(value=v)) for k, v in filters.items()]
        q_filter = models.Filter(must=must_conditions)

        all_hits = []
        scroll_id = None
        while True:
            hits, scroll_id = manager.client.scroll(
                collection_name=col,
                scroll_filter=q_filter,
                limit=min(100, limit - len(all_hits)),
                with_payload=True,
                with_vectors=with_vectors,
            )
            all_hits.extend(hits)
            if not scroll_id or len(all_hits) >= limit:
                break

        results = [
            {"id": h.id, "payload": h.payload, "score": getattr(h, "score", None)}
            for h in all_hits[:limit]
        ]

        logger.info(f"[FilterSearch] Found {len(results)} results in '{col}' matching {filters}")
        return results

    except Exception as exc:  # noqa: BLE001
        logger.error(f"[FilterSearch] Error searching in {col}: {exc}")
        return []
