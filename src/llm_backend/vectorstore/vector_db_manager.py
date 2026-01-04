# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import warnings
from typing import Any, Dict, List, Optional, Callable
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance
from qdrant_client.models import (
    SparseVector,
)

# --- Logging & Debug Utils ---
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.utils.id_helper import make_hash_id_from_path


# ---- External Modules ----
from .config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    SNAPSHOT_DIR,
    VECTOR_SIZE,
    DEFAULT_COLLECTION_NAME,
)
from .sparse_engine import bm25_encode, splade_encode
from .sparse_engine import init_sparse_engine as sparse_init_service
from .sparse_engine import fit_from_folder as sparse_fit_service
from .vector_db_helper import query_unique_docs as qdrant_query_unique_docs
from .search_pipeline import run_query_pipeline
from .collection_manager import (
    create_collection as create_collection_helper,
)
from .ingest_manager import (
    delete_by_filter as delete_by_filter_helper,
    delete_document as delete_document_helper,
    filter_search as filter_search_helper,
    update_payload as update_payload_helper,
    upsert_document as upsert_document_helper,
    upsert_folder as upsert_folder_helper,
)
from .snapshot_manager import (
    create_snapshot as create_snapshot_service,
    delete_snapshot as delete_snapshot_service,
    list_snapshots as list_snapshots_service,
    restore_snapshot as restore_snapshot_service,
)

warnings.filterwarnings("ignore", message="BertForMaskedLM has generative capabilities")


def _norm_doc_key(x):
    """Normalize id to match Qdrant payload parent_id/id (remove dash, lowercase)."""
    if x is None:
        return None
    return str(x).replace("-", "").lower()


# -------------------------------------------------------
# VectorDBManager
# -------------------------------------------------------
class VectorDBManager:
    """
    Qdrant-based multi-collection vector DB manager.
    - Create / Read / Update / Delete / Query
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_collection: Optional[str] = None,
        pipeline_config: Optional[Dict[str, Any]] = None,
    ):
        trace("Initializing VectorDBManager")
        self.client = QdrantClient(
            url=url or QDRANT_URL,
            api_key=api_key or QDRANT_API_KEY,
            prefer_grpc=False,
            check_compatibility=False,
            timeout=300,
        )
        self.default_collection = default_collection or DEFAULT_COLLECTION_NAME

        # 모델 핸들
        from .embedding import get_model

        self._dense_model_getter = get_model
        self.bm25_encode = bm25_encode
        self.splade_encode = splade_encode

        self._cross_tokenizer = None
        self._cross_model = None
        self._cross_model_name = None

        # Load default config from settings
        from .config import PIPELINE_CONFIG

        self.pipeline_config = PIPELINE_CONFIG.copy()

        if pipeline_config:
            self.pipeline_config.update(pipeline_config)

        logger.info(f"VectorDBManager initialized. Default={self.default_collection}")

    @property
    def dense_model(self):
        return self._dense_model_getter()

    # ------------ Create / Init ------------

    def list_collections_info(self) -> List[Dict[str, Any]]:
        """
        Retrieve state of all collections (name, doc count, etc).
        """
        trace("list_collections_info()")
        try:
            resp = self.client.get_collections()
            result = []
            for desc in resp.collections:
                name = desc.name
                # 문서 수 조회
                try:
                    count_resp = self.client.count(collection_name=name)
                    count = count_resp.count
                except Exception:
                    count = 0

                # 상세 정보 (Vector Size 등)
                size = None
                status = "unknown"
                try:
                    info = self.client.get_collection(collection_name=name)
                    # Qdrant client 1.x structure: info.config.params.vectors
                    if info and info.config and info.config.params:
                        vecs = info.config.params.vectors

                        # 1. Single Vector
                        if hasattr(vecs, "size") and vecs.size is not None:
                            size = vecs.size

                        # 2. Named Vectors (e.g. 'dense', 'sparse'...)
                        # Check dict-like or object with attributes
                        else:
                            # Prioritize 'dense'
                            dense_p = None
                            if isinstance(vecs, dict):
                                dense_p = vecs.get("dense")
                            elif hasattr(vecs, "dense"):
                                dense_p = vecs.dense

                            # If 'dense' found, get size
                            if dense_p and hasattr(dense_p, "size"):
                                size = dense_p.size

                    if info:
                        status = str(info.status)
                except Exception:
                    # logger.warning(f"Failed to get info for {name}: {e}")
                    pass

                result.append(
                    {
                        "name": name,
                        "count": count,
                        "vector_size": size,
                        "status": str(status),
                    }
                )
            return result
        except Exception as e:
            logger.error(f"[VectorManager] List collections failed: {e}")
            return []

    def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: str | Distance = "Cosine",
        force: bool = False,
        include_sparse: bool = True,
        include_splade: bool = True,
        use_quantization: bool = True,
    ):
        trace(f"create_collection({name}, quant={use_quantization})")
        create_collection_helper(
            manager=self,
            name=name,
            vector_size=vector_size,
            distance=distance,
            force=force,
            include_sparse=include_sparse,
            include_splade=include_splade,
            use_quantization=use_quantization,
        )

        # --- Multi-Tenancy Foundation ---
        # Create indexes for fast filtering by tenant and access level
        try:
            logger.info(f"[MultiTenancy] Creating payload indexes for {name}")
            self.client.create_payload_index(
                collection_name=name,
                field_name="tenant_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=name,
                field_name="access_level",
                field_schema=models.PayloadSchemaType.INTEGER,
            )
        except Exception as e:
            logger.warning(f"[MultiTenancy] Failed to create indexes: {e}")

    def initialize_collections(self, config: Dict[str, Dict[str, Any]]):
        trace("initialize_collections()")
        for name, spec in config.items():
            self.create_collection(
                name,
                spec.get("vector_size", 768),
                spec.get("distance", "Cosine"),
                spec.get("force", False),
            )
        logger.info(f"Initialized {len(config)} collections")

        # ------------ Snapshot Management ------------

    def create_snapshot(
        self, collection: Optional[str] = None, dest_dir: str = "./snapshots"
    ):
        return create_snapshot_service(self, collection=collection, dest_dir=dest_dir)

    def list_snapshots(self, collection: Optional[str] = None):
        return list_snapshots_service(self, collection=collection)

    def restore_snapshot(self, collection: str, snapshot_path: str):
        return restore_snapshot_service(self, collection, snapshot_path)

    def delete_snapshot(self, collection: str, snapshot_name: str):
        return delete_snapshot_service(self, collection, snapshot_name)

    # ------------ Sparse Engine 학습 및 초기화 ------------
    def fit_bm25_from_json_folder(self, base_path: str) -> int:
        return sparse_fit_service(base_path)

    def init_bm25(self, base_path: str = "./data", force_retrain: bool = False):
        sparse_init_service(data_path=base_path, force_retrain=force_retrain)

    # ------------ Upsert ------------
    def make_doc_hash_id(self, path: str) -> str:
        return make_hash_id_from_path(path)

    def upsert_folder(
        self,
        folder: str,
        collection: str,
        batch_size: int = 50,
        progress_callback: Optional[Callable[[float], None]] = None,
    ):
        trace(f"upsert_folder({folder}, {collection}, batch_size={batch_size})")
        upsert_folder_helper(
            self,
            folder,
            collection,
            batch_size=batch_size,
            progress_callback=progress_callback,
        )

    def upsert_documents(
        self,
        col: str,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> int:
        """
        Batch upsert documents from memory.
        """
        from .ingest_manager import upsert_batch_documents

        trace(f"upsert_documents({col}, count={len(documents)})")
        return upsert_batch_documents(
            self, col, documents, progress_callback=progress_callback
        )

    def upsert_document(self, col: str, data: dict, doc_id: Optional[str] = None):
        """
        Upsert a single document to Qdrant collection.
        - Generate db_id based on JSON hash to prevent duplicates.
        - Qdrant point ID always uses UUID.
        - Original id / parent_id kept in payload only.
        """
        trace(f"upsert_document({col}, id={doc_id})")
        upsert_document_helper(self, col, data, doc_id)

    # ------------ Query ------------
    # ------------------------------------------------------
    # SEARCH (Dense/Sparse/SPLADE 각각 수행)
    # ------------------------------------------------------
    def _search_collection_unique(
        self, collection, query_text, top_k, use_dense, use_sparse, use_splade
    ):
        trace(f"Searching unique docs from {collection}")
        dense_results, sparse_results, splade_results = [], [], []

        if use_dense:
            dense_vec = self.embedding_models["dense"].encode(
                query_text, show_progress_bar=False
            )
            dense_results = qdrant_query_unique_docs(
                self.client, collection, dense_vec, "dense", top_k
            )

        if use_sparse:
            bm25_vec = bm25_encode(query_text)
            bm25_vec = SparseVector(
                indices=list(bm25_vec.keys()), values=list(bm25_vec.values())
            )
            sparse_results = qdrant_query_unique_docs(
                self.client, collection, bm25_vec, "sparse", top_k
            )

        if use_splade:
            sp_vec = splade_encode(query_text)
            sp_vec = SparseVector(
                indices=[int(k) for k in sp_vec.keys()],
                values=[float(v) for v in sp_vec.values()],
            )
            splade_results = qdrant_query_unique_docs(
                self.client, collection, sp_vec, "splade", top_k
            )

        return dense_results, sparse_results, splade_results

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        collections: Optional[List[str]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Run hybrid search via DualPathOrchestrator.

        Phase 8: Enables split Primary/Recommendation logic and preserves original query.
        Phase 15: Accepts user_context for RBAC.
        """

        trace(f"query('{query_text[:20]}...')")
        collections = collections or [self.default_collection]

        from .dual_path import DualPathOrchestrator

        # Phase 19: Support pipeline overrides (alpha, etc.)
        pipeline_overrides = kwargs.get("pipeline_overrides", {})

        orchestration_res = DualPathOrchestrator.process_query(
            manager=self,
            query_text=query_text,
            top_k=top_k,
            collections=collections,
            user_context=user_context,
            pipeline_overrides=pipeline_overrides,
        )
        return orchestration_res["results"]

    def search_keyword(
        self,
        query_text: str,
        top_k: int = 10,
        collections: Optional[List[str]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform simple keyword search (BM25 only).
        Disables Dense and SPLADE vectors for this query.
        """
        trace(f"search_keyword('{query_text[:20]}...')")

        # Create a temporary config overriding weights
        # We want only sparse (BM25)
        temp_cfg = self.pipeline_config.copy()
        temp_cfg["use_dense"] = False
        temp_cfg["use_splade"] = False
        temp_cfg["use_sparse"] = True
        temp_cfg["sparse_weight"] = 1.0

        # Disable reranker for pure keyword speed/nature?
        # Usually keyword search implies simple retrieval. Let's keep reranker optional or disable it.
        # User asked for "simple keyword search". Let's disable reranker to be specific.
        temp_cfg["use_reranker"] = False

        collections = collections or [self.default_collection]

        return run_query_pipeline(
            manager=self,
            query_text=query_text,
            top_k=top_k,
            collections=collections,
            cfg=temp_cfg,
            user_context=user_context,
        )

        # ------------ Filter Search ------------

    def filter_search(
        self,
        col: str,
        filters: Dict[str, Any],
        limit: int = 10,
        with_vectors: bool = False,
    ):
        """
        Qdrant Filter-based search (payload conditions only).
        Searches without vector calculation.

        Args:
            col (str): Collection name
            filters (dict): key=value conditions, e.g. {"category": "AI", "verified": True}
            limit (int): Max docs to return
            with_vectors (bool): If True, include vectors.
        """
        trace(f"filter_search({col}, filters={filters})")
        return filter_search_helper(
            self, col, filters, limit=limit, with_vectors=with_vectors
        )

        # ------------ Update (Payload Only) ------------

    def update_payload(
        self, col: str, doc_id: str, new_payload: dict, merge: bool = True
    ):
        """
        Update document payload in Qdrant. No vector recalculation.

        Args:
            col (str): Target collection
            doc_id (str): Document ID
            new_payload (dict): New payload values
            merge (bool): If True, merge with existing payload.
        """
        trace(f"update_payload({col}, id={doc_id}, merge={merge})")
        try:
            # 기존 payload 불러오기
            result = self.client.retrieve(
                collection_name=col, ids=[doc_id], with_payload=True
            )

            if not result:
                logger.warning(
                    f"[UpdatePayload] Document not found in {col}: id={doc_id}"
                )
                return False

            return update_payload_helper(self, col, doc_id, new_payload, merge=merge)

        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"[UpdatePayload] Error updating payload for id={doc_id}: {exc}"
            )
            return False

    def delete_document(self, col: str, db_id: str) -> bool:
        """
        Delete single document from Qdrant by db_id.

        Args:
            col (str): Collection name
            db_id (str): Unique document ID (SHA-256)
        """
        trace(f"delete_document({col}, db_id={db_id[:12]}...)")
        return delete_document_helper(self, col, db_id)

    def get_document(self, col: str, db_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single document's payload by its db_id.
        """
        trace(f"get_document({col}, db_id={db_id[:12]}...)")
        try:
            # 1. Try direct retrieval by ID (since we use deterministic IDs, db_id might match point_id logic)
            # Actually, our point_id is uuid5(NAMESPACE, db_id), so we can theoretically compute point_id if strictly needed.
            # But simpler to just query by Point ID if we knew it found it, OR use scroll filter by db_id payload.

            # Since we didn't expose point_id regeneration logic easily here, let's use Scroll by payload 'db_id'
            # OR 'id' matches.

            # BEST EFFORT:
            # Try to retrieve using the db_id as point_id (in case they passed the UUID)
            # If not found, use filter search on 'db_id' payload field.

            # However, user likely passes the content-hash string 'db_id'.

            hits, _ = self.client.scroll(
                collection_name=col,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="db_id", match=models.MatchValue(value=db_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False,
            )

            if hits:
                return {
                    "id": hits[0].id,
                    "payload": hits[0].payload,
                    "score": getattr(hits[0], "score", None),
                }

            logger.warning(f"[GetDocument] Not found: {db_id} in {col}")
            return None

        except Exception as e:
            logger.error(f"[GetDocument] Error retrieving {db_id}: {e}")
            return None

    def get_documents(self, col: str, db_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve multiple documents by their db_ids (Batch).
        Returns a list of found documents with their payloads.
        """
        trace(f"get_documents({col}, count={len(db_ids)})")
        if not db_ids:
            return []

        try:
            # Use MatchAny to fetch all matching documents in one query
            # Note: The result order is not guaranteed to match input order.

            # Qdrant scroll has a limit. If len(db_ids) is large, we might need multiple scrolls or just set a large limit.
            # Assuming batch size is reasonable (<1000). safely using len(db_ids) + buffer.

            limit = len(db_ids)
            hits, _ = self.client.scroll(
                collection_name=col,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="db_id", match=models.MatchAny(any=db_ids)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            results = []
            for h in hits:
                results.append(
                    {
                        "id": h.id,
                        "payload": h.payload,
                        "score": getattr(h, "score", None),
                    }
                )

            logger.info(
                f"[GetDocuments] Found {len(results)}/{len(db_ids)} docs in {col}"
            )
            return results

        except Exception as e:
            logger.error(f"[GetDocuments] Error retrieving batch: {e}")
            return []

    def delete_by_filter(self, col: str, field: str, value: Any) -> int:
        """
        Batch delete documents by field value.
        Example: delete_by_filter("notion.marketing", "category", "AI")

        Args:
            col (str): Collection name
            field (str): Field name
            value (Any): Match value
        """
        trace(f"delete_by_filter({col}, field={field}, value={value})")
        return delete_by_filter_helper(self, col, field, value)

    def auto_initialize(self, base_folder="./data", snapshot_dir=SNAPSHOT_DIR):
        """
        서버 시작 시 VectorDB 상태를 자동 초기화:
        1. 최신 스냅샷 존재 → 복원
        2. 없으면 → 컬렉션 생성 + 데이터 업서트 + BM25 학습
        """
        trace("[Init] Auto-initializing VectorDB state...")
        os.makedirs(snapshot_dir, exist_ok=True)

        # 최신 스냅샷 존재 확인
        snapshots = sorted(
            [f for f in os.listdir(snapshot_dir) if f.endswith(".zip")],
            key=lambda x: os.path.getmtime(os.path.join(snapshot_dir, x)),
            reverse=True,
        )

        if snapshots:
            latest = snapshots[0]
            logger.info(f"[Init] Found snapshot: {latest} - restoring...")
            self.restore_snapshot(
                self.default_collection, os.path.join(snapshot_dir, latest)
            )
        else:
            logger.warning(
                "[Init] No snapshot found - creating collection from local data"
            )
            self.create_collection(self.default_collection, vector_size=VECTOR_SIZE)
            self.init_bm25(base_path=base_folder)
            self.upsert_folder(
                os.path.join(base_folder, DEFAULT_COLLECTION_NAME.replace(".", "/")),
                self.default_collection,
            )
            self.create_snapshot(self.default_collection, snapshot_dir)

    # ------------ Logging ------------
    def log_results(self, results: List[Dict[str, Any]], title="Results", top_n=10):
        logger.info(f"--- {title} ---")
        if not results:
            logger.warning("No results to display.")
            return

        for i, r in enumerate(results[:top_n], 1):
            rid = r.get("db_id") or r.get("id") or r.get("doc_id") or "unknown_id"
            scr = r.get("final_score") or r.get("score") or r.get("avg_score") or 0.0
            t = r.get("title") or r.get("text") or r.get("content") or ""
            col = r.get("collection", self.default_collection)

            # Fallback for non-string values
            if not isinstance(t, str):
                t = str(t) if t is not None else ""

            logger.info(f"{i:02d}. {col} | {rid} | {t[:30]} | score={scr:.4f}")

        logger.info("-----------------------------------\n")
