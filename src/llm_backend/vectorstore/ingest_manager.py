"""Ingestion and payload operations for Qdrant via VectorDBManager."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Callable

from qdrant_client import models
from qdrant_client.models import SparseVector

from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.utils.id_helper import (
    make_hash_id_from_path,
    make_doc_hash_id_from_json,
    generate_point_id,
)

from llm_backend.vectorstore.sparse_engine import bm25_encode, splade_encode


def make_doc_hash_id(path: str) -> str:
    return make_hash_id_from_path(path)


def upsert_batch_documents(
    manager,
    collection: str,
    docs: List[Dict[str, Any]],
    progress_callback: Optional[Callable[[float], None]] = None,
) -> int:
    """
    Public batch upsert function.
    """
    if not docs:
        return 0

    total_docs = len(docs)
    # Process in batches of 100 to report progress and maintain memory efficiency
    internal_batch_size = 100
    total_upserted = 0

    from llm_backend.vectorstore.chunking import SimpleRecursiveChunker
    from llm_backend.vectorstore.json_handler import JSONProcessor

    chunker = SimpleRecursiveChunker(chunk_size=1000, chunk_overlap=200)

    for batch_start in range(0, total_docs, internal_batch_size):
        batch_docs = docs[batch_start : batch_start + internal_batch_size]

        try:
            # Auto-create collection on first batch if needed
            if batch_start == 0:
                try:
                    manager.client.get_collection(collection_name=collection)
                except Exception as e:
                    if "not found" in str(e).lower() or "404" in str(e):
                        from llm_backend.vectorstore.config import VECTOR_SIZE

                        manager.create_collection(collection, vector_size=VECTOR_SIZE)
                    else:
                        raise e

            texts, valid_docs = [], []
            for d in batch_docs:
                d = JSONProcessor.process_document(d)
                content = d.get("content") or ""
                if not isinstance(content, str) or not content.strip():
                    continue

                # Document-level ID (before chunking)
                doc_db_id = make_doc_hash_id_from_json(d)
                
                chunks = chunker.split_text(content)
                for i, chunk_text in enumerate(chunks):
                    chunk_doc = d.copy()
                    chunk_doc.update(
                        {
                            "content": chunk_text,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "is_chunk": True,
                            "db_id": doc_db_id,
                            "parent_id": d.get("id") or doc_db_id,
                        }
                    )
                    texts.append(chunk_text)
                    valid_docs.append(chunk_doc)

            if not texts:
                continue

            # Batch Encoding - Disable internal progress bar as we have custom progress tracking
            dense_vecs = manager.dense_model.encode(
                texts, batch_size=4, show_progress_bar=False
            )
            bm25_vecs_list = bm25_encode(texts)
            
            # SPLADE Toggle (Default: Enabled if not specified, but let's allow disabling)
            # To fix OOM, User can set ENABLE_SPLADE=0
            enable_splade = os.getenv("ENABLE_SPLADE", "1") == "1"
            
            splade_vecs_list = []
            if enable_splade:
                try:
                    splade_vecs_list = splade_encode(texts)
                except Exception:
                    splade_vecs_list = [{} for _ in texts]
            else:
                splade_vecs_list = [{} for _ in texts]

            # Create Points
            points = []
            for i, doc in enumerate(valid_docs):
                db_id = doc.get("db_id")
                # Point ID must be unique across chunks, but deterministic per chunk
                point_id = generate_point_id(db_id, chunk_index=doc.get("chunk_index", 0))

                b_vec = bm25_vecs_list[i]
                bm25_sv = models.SparseVector(
                    indices=[int(k) for k in b_vec.keys()], values=list(b_vec.values())
                )
                
                s_vec = splade_vecs_list[i]
                splade_sv = models.SparseVector(
                    indices=[int(k) for k in s_vec.keys()], values=list(s_vec.values())
                )
                d_vec = dense_vecs[i].tolist()

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector={"dense": d_vec, "sparse": bm25_sv, "splade": splade_sv},
                        payload={
                            **doc,
                            "id": doc.get("id", db_id),
                            "parent_id": doc.get("parent_id", db_id),
                            "db_id": db_id,
                            "tenant_id": doc.get("tenant_id", "public"),
                            "access_level": doc.get("access_level", 1),
                        },
                    )
                )

            if points:
                manager.client.upsert(collection_name=collection, points=points)
                total_upserted += len(batch_docs)

            if progress_callback:
                progress = (
                    min(batch_start + internal_batch_size, total_docs) / total_docs
                ) * 100
                progress_callback(min(progress, 99.0))  # 100 is set by the task caller

        except Exception as e:
            logger.error(f"[Upsert] Batch failed: {e}")
            raise

    return total_upserted


def upsert_folder(
    manager,
    folder: str,
    collection: str,
    batch_size: int = 50,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> None:
    trace(f"upsert_folder({folder}, {collection}, batch_size={batch_size})")

    if not os.path.exists(folder):
        logger.warning(f"Folder not found: {folder}")
        return

    # Recursive File Finding
    files = []
    for root, _, filenames in os.walk(folder):
        for filename in filenames:
            if filename.endswith(".json") or filename.endswith(".jsonl"):
                files.append(os.path.join(root, filename))

    total = len(files)
    if total == 0:
        logger.warning(f"No JSON/JSONL files found in {folder} (recursively)")
        return

    logger.info(
        f"Upserting {total} files from {folder} into '{collection}' (Batch Size: {batch_size})"
    )

    batch_data = []
    success_count = 0
    fail_count = 0

    # Process files
    for idx, file_path in enumerate(files, 1):
        try:
            current_file_docs = []
            
            with open(file_path, "r", encoding="utf-8") as fp:
                # Handle JSONL
                if file_path.endswith(".jsonl"):
                    for line in fp:
                        if line.strip():
                            current_file_docs.append(json.loads(line))
                # Handle JSON
                else:
                    data = json.load(fp)
                    if isinstance(data, list):
                        current_file_docs.extend(data)
                    else:
                        current_file_docs.append(data)

            # Add to batch
            batch_data.extend(current_file_docs)

            # Flush if batch is full
            while len(batch_data) >= batch_size:
                # Slice logic to respect exact batch size if needed
                chunk = batch_data[:batch_size]
                batch_data = batch_data[batch_size:]
                
                succeeded = upsert_batch_documents(manager, collection, chunk)
                success_count += succeeded

                if progress_callback:
                    progress = (idx / total) * 100
                    progress_callback(min(progress, 99.0))

        except Exception as exc:
            fail_count += 1
            logger.error(f"[Upsert Fail] File read error {file_path}: {exc}")

    # Final Flush
    if batch_data:
        succeeded = upsert_batch_documents(manager, collection, batch_data)
        success_count += succeeded

    logger.info(f"Finished upserting '{collection}' — {success_count} succeeded docs.")


def upsert_document(
    manager, col: str, data: dict, doc_id: Optional[str] = None
) -> None:
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
            logger.warning(
                f"[Upsert] Skip doc without content in '{col}' (id={doc_id})"
            )
            return

        json.dumps(data, sort_keys=True, ensure_ascii=False)
        db_id = make_doc_hash_id_from_json(data)
        data["db_id"] = db_id

        dense_vec = manager.dense_model.encode(content, show_progress_bar=False)
        bm25_vec = bm25_encode(content)
        bm25_sv = SparseVector(
            indices=list(bm25_vec.keys()), values=list(bm25_vec.values())
        )

        # SPLADE는 실패해도 업서트를 계속 진행 (dense+BM25만 저장)
        try:
            splade_vec = splade_encode(content)
            splade_sv = SparseVector(
                indices=list(splade_vec.keys()), values=list(splade_vec.values())
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"[Upsert] SPLADE encoding failed; storing dense+BM25 only: {exc}"
            )
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
                from llm_backend.server.vector_server.core.security.encryption_manager import (
                    EncryptionManager,
                )

                encryptor = EncryptionManager.get_instance()
                stored_content = encryptor.encrypt_text(tenant_id, content)
                is_encrypted = True
            except Exception as e:
                logger.error(
                    f"[Upsert] Encryption failed for {doc_id} (tenant={tenant_id}): {e}"
                )
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
            "content_encrypted": is_encrypted,
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


def update_payload(
    manager, col: str, doc_id: str, new_payload: dict, merge: bool = True
) -> bool:
    trace(f"update_payload({col}, id={doc_id}, merge={merge})")
    try:
        result = manager.client.retrieve(
            collection_name=col, ids=[doc_id], with_payload=True
        )
        if not result:
            logger.warning(f"[UpdatePayload] Document not found in {col}: id={doc_id}")
            return False

        old_payload = result[0].payload or {}
        updated_payload = {**old_payload, **new_payload} if merge else new_payload

        manager.client.set_payload(
            collection_name=col, payload=updated_payload, points=[doc_id]
        )
        logger.info(f"[UpdatePayload] Updated payload for doc_id={doc_id} in '{col}'")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[UpdatePayload] Error updating payload for id={doc_id}: {exc}")
        return False


def delete_document(manager, col: str, db_id: str) -> bool:
    trace(f"delete_document({col}, db_id={db_id[:12]}...)")
    try:
        # Use Filter to delete ALL chunks and potential parent sharing this db_id
        manager.client.delete(
            collection_name=col,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(key="db_id", match=models.MatchValue(value=db_id))
                ]
            ),
        )
        logger.info(
            f"[Delete] Deleted document (including all chunks) with db_id={db_id[:12]}... from '{col}'"
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            f"[Delete] Error deleting db_id={db_id[:12]}... from '{col}': {exc}"
        )
        return False


def delete_by_filter(manager, col: str, field: str, value: Any) -> int:
    trace(f"delete_by_filter({col}, field={field}, value={value})")
    try:
        condition = models.Filter(
            must=[
                models.FieldCondition(key=field, match=models.MatchValue(value=value))
            ]
        )
        result = manager.client.delete(
            collection_name=col,
            points_selector=condition,
        )
        deleted_count = getattr(result, "result", {}).get("num_points", 0)
        logger.info(
            f"[DeleteByFilter] Deleted {deleted_count} docs from '{col}' where {field}={value}"
        )
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
        must_conditions = [
            models.FieldCondition(key=k, match=models.MatchValue(value=v))
            for k, v in filters.items()
        ]
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

        logger.info(
            f"[FilterSearch] Found {len(results)} results in '{col}' matching {filters}"
        )
        return results

    except Exception as exc:  # noqa: BLE001
        logger.error(f"[FilterSearch] Error searching in {col}: {exc}")
        return []
