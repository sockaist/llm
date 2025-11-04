# -*- coding: utf-8 -*-
from __future__ import annotations
import os, math, warnings, hashlib
from typing import Any, Dict, List, Optional, Tuple
from tqdm import tqdm
import uuid
import json, hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, SparseIndexParams,
    PointStruct, Filter, FieldCondition, MatchValue, NamedVector,
    FilterSelector, SparseVector,
)
from qdrant_client.http.models import ScoredPoint
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList

# --- 로깅 & 디버깅 유틸 ---
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.utils.id_helper import make_hash_id_from_path, make_doc_hash_id_from_json


warnings.filterwarnings("ignore", message="BertForMaskedLM has generative capabilities")

# ---- 외부 모듈(이미 주어진 코드들) ----
from .config import QDRANT_URL, QDRANT_API_KEY, DISTANCE, FORMATS
from .embedding import model as dense_sbert_model
from .embedding import content_embedder
from .sparse_helper import bm25_encode, bm25_fit
from .splade_module import splade_encode
from .vector_db_helper import create_doc_upsert, query_unique_docs as qdrant_query_unique_docs
from .reranker_module import (
    weighted_fuse, deduplicate_and_average as dedup_avg_by_doc,
    load_cross_encoder, rerank_with_cross_encoder, apply_date_window_boost
)

def _norm_doc_key(x):
    """Qdrant payload의 parent_id/id와 매칭되도록 id를 정규화 (대시 제거, 소문자)."""
    if x is None:
        return None
    return str(x).replace("-", "").lower()


# -------------------------------------------------------
# VectorDBManager
# -------------------------------------------------------
class VectorDBManager:
    """
    Qdrant 기반 멀티 컬렉션 벡터 DB 매니저
    - Create / Read / Update / Delete / Query
    """

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None,
                 default_collection: Optional[str] = None,
                 pipeline_config: Optional[Dict[str, Any]] = None):
        trace("Initializing VectorDBManager")
        self.client = QdrantClient(url=url or QDRANT_URL, api_key=api_key or QDRANT_API_KEY)
        self.default_collection = default_collection or "notion.marketing"

        # 모델 핸들
        self.embedding_models = {"dense": dense_sbert_model}
        self.dense_model = dense_sbert_model
        self.bm25_encode = bm25_encode
        self.splade_encode = splade_encode

        self._cross_tokenizer = None
        self._cross_model = None
        self._cross_model_name = None

        self.pipeline_config = {
            "use_dense": True, "use_sparse": True, "use_splade": True,
            "use_reranker": True, "use_date_boost": True,
            "dense_weight": 0.6, "sparse_weight": 0.3, "splade_weight": 0.1,
            "cross_encoder_model": "Dongjin-kr/ko-reranker",
            "date_decay_rate": 0.03, "date_weight": 0.45,
            "date_from": None, "date_to": None,
        }
        if pipeline_config:
            self.pipeline_config.update(pipeline_config)
        from .sparse_helper import bm25_fit, bm25_load, BM25_PATH
                # ======================================================
        # (추가) BM25 초기화 로직
        # ======================================================
        try:
            from .sparse_helper import bm25_load, bm25_fit, BM25_PATH
            if os.path.exists(BM25_PATH):
                bm25_load()
                logger.info(f"[BM25] Loaded existing vectorizer from {BM25_PATH}")
            else:
                logger.warning(f"[BM25] No saved vectorizer found — will require training later.")
        except Exception as e:
            logger.error(f"[BM25] Initialization failed: {e}")
        logger.info(f"VectorDBManager initialized. Default={self.default_collection}")

    # ------------ Create / Init ------------
    # ------------ Create / Init ------------
    def create_collection(self, name: str, vector_size: int,
                        distance: str | Distance = "Cosine", force: bool = False,
                        include_sparse: bool = True, include_splade: bool = True):
        trace(f"create_collection({name})")
        try:
            if isinstance(distance, str):
                distance = {
                    "Cosine": Distance.COSINE,
                    "Dot": Distance.DOT,
                    "Euclid": Distance.EUCLID
                }.get(distance, Distance.COSINE)

            # 기존 컬렉션 삭제 (옵션)
            if force:
                self.client.delete_collection(name)

            # --- 벡터 설정 ---
            vectors_cfg = {"dense": VectorParams(size=vector_size, distance=distance)}
            sparse_cfg = {}
            if include_sparse:
                sparse_cfg["sparse"] = SparseVectorParams(index=SparseIndexParams(on_disk=False))
            if include_splade:
                sparse_cfg["splade"] = SparseVectorParams(index=SparseIndexParams(on_disk=False))

            # --- 컬렉션 재생성 ---
            self.client.recreate_collection(
                collection_name=name,
                vectors_config=vectors_cfg,
                sparse_vectors_config=sparse_cfg if sparse_cfg else None
            )
            logger.info(f"Created collection '{name}' ({vector_size}D, {distance})")

            # (신규 추가) db_id 인덱스 자동 생성
            try:
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="db_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                    wait=True,
                )
                logger.info(f"[create_collection] Created 'db_id' payload index for '{name}'")
            except Exception as e:
                logger.warning(f"[create_collection] Failed to create payload index for '{name}': {e}")

        except Exception as e:
            logger.error(f"[create_collection] Error: {e}")
            raise

    def initialize_collections(self, config: Dict[str, Dict[str, Any]]):
        trace("initialize_collections()")
        for name, spec in config.items():
            self.create_collection(
                name, spec.get("vector_size", 768),
                spec.get("distance", "Cosine"),
                spec.get("force", False)
            )
        logger.info(f"Initialized {len(config)} collections")
        
        # ------------ Snapshot Management ------------
    def create_snapshot(self, collection: Optional[str] = None, dest_dir: str = "./snapshots"):
        """
        지정한 컬렉션의 Qdrant 스냅샷을 생성하고 로컬에 저장.
        - snapshot 파일은 ZIP 형태로 저장됨.
        """
        from datetime import datetime
        os.makedirs(dest_dir, exist_ok=True)
        col = collection or self.default_collection

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            logger.info(f"[Snapshot] Creating snapshot for '{col}'...")
            snapshot = self.client.create_snapshot(collection_name=col, wait=True)
            snap_name = snapshot.name
            snap_path = os.path.join(dest_dir, f"{col}_{timestamp}.zip")

            # 서버에 생성된 snapshot 다운로드
            self.client.download_snapshot(collection_name=col, snapshot_name=snap_name, path=snap_path)
            logger.info(f"[Snapshot] Saved snapshot to: {snap_path}")
            return {"status": "ok", "collection": col, "snapshot": snap_path}

        except Exception as e:
            logger.error(f"[Snapshot Error] {e}")
            return {"status": "error", "detail": str(e)}

    def list_snapshots(self, collection: Optional[str] = None):
        """
        Qdrant 서버 상의 컬렉션 스냅샷 목록 조회
        """
        col = collection or self.default_collection
        try:
            snapshots = self.client.list_snapshots(collection_name=col)
            result = [{"name": s.name, "created": str(s.creation_time)} for s in snapshots]
            logger.info(f"[Snapshot] {len(result)} snapshots found for '{col}'")
            return result
        except Exception as e:
            logger.error(f"[Snapshot List Error] {e}")
            return []

    def restore_snapshot(self, collection: str, snapshot_path: str):
        """
        지정한 ZIP 스냅샷 파일로 컬렉션 복원
        """
        try:
            logger.info(f"[Snapshot] Restoring collection '{collection}' from '{snapshot_path}'")
            self.client.recover_snapshot(collection_name=collection, location=snapshot_path)
            logger.info(f"[Snapshot] '{collection}' successfully restored.")
            return {"status": "ok", "collection": collection}
        except Exception as e:
            logger.error(f"[Snapshot Restore Error] {e}")
            return {"status": "error", "detail": str(e)}

    def delete_snapshot(self, collection: str, snapshot_name: str):
        """
        Qdrant 서버 상의 특정 스냅샷 삭제
        """
        try:
            logger.info(f"[Snapshot] Deleting snapshot '{snapshot_name}' from '{collection}'")
            self.client.delete_snapshot(collection_name=collection, snapshot_name=snapshot_name)
            logger.info(f"[Snapshot] Deleted snapshot '{snapshot_name}'")
            return {"status": "ok", "deleted": snapshot_name}
        except Exception as e:
            logger.error(f"[Snapshot Delete Error] {e}")
            return {"status": "error", "detail": str(e)}

    # ------------ BM25 학습 ------------
    def fit_bm25_from_json_folder(self, base_path: str) -> int:
        trace(f"fit_bm25_from_json_folder({base_path})")
        import json
        all_texts = []
        for root, _, files in os.walk(base_path):
            for f in files:
                if not f.endswith(".json"): continue
                try:
                    with open(os.path.join(root, f), "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        txt = data.get("content") or data.get("contents")
                        if txt: all_texts.append(txt)
                except Exception: continue
        if not all_texts:
            raise RuntimeError("No data for BM25 fitting")
        bm25_fit(all_texts)
        logger.info(f"[BM25] Trained on {len(all_texts)} docs.")
        return len(all_texts)

        # ------------ BM25 (재)초기화 ------------
    def init_bm25(self, base_path: str = "./data", force_retrain: bool = False):
        """
        BM25 벡터라이저를 초기화합니다.
        - force_retrain=True일 경우 기존 저장된 모델 삭제 후 재학습
        - 기존 모델이 있으면 자동 로드
        """
        from .sparse_helper import bm25_fit, bm25_load, BM25_PATH
        trace(f"init_bm25(base_path={base_path}, force_retrain={force_retrain})")

        if force_retrain and os.path.exists(BM25_PATH):
            os.remove(BM25_PATH)
            logger.warning(f"[BM25] Existing model at {BM25_PATH} removed (force_retrain=True)")

        if os.path.exists(BM25_PATH):
            bm25_load()
            logger.info(f"[BM25] Loaded existing model from {BM25_PATH}")
        else:
            # 새 학습 실행
            logger.info("[BM25] No existing model found. Training new BM25 vectorizer...")
            num_docs = self.fit_bm25_from_json_folder(base_path)
            logger.info(f"[BM25] Trained on {num_docs} documents and saved to {BM25_PATH}")
            
    # ------------ Upsert ------------
    def make_doc_hash_id(self, path: str) -> str:
        return make_hash_id_from_path(path)

    def upsert_folder(self, folder: str, collection: str):
        trace(f"upsert_folder({folder}, {collection})")
        import json

        if not os.path.exists(folder):
            logger.warning(f"Folder not found: {folder}")
            return

        files = [f for f in os.listdir(folder) if f.endswith(".json")]
        total = len(files)
        if total == 0:
            logger.warning(f"No JSON files found in {folder}")
            return

        logger.info(f"Upserting {total} JSON files into '{collection}'")

        success, fail = 0, 0
        for idx, f in enumerate(files, 1):
            try:
                file_path = os.path.join(folder, f)
                with open(file_path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                doc_id = self.make_doc_hash_id(f)
                self.upsert_document(collection, data, doc_id)
                success += 1
            except Exception as e:
                fail += 1
                logger.error(f"[Upsert Fail] {f}: {e}")

            # 매 10개마다 혹은 마지막에만 진행률 로그
            if idx % 10 == 0 or idx == total:
                logger.info(f"[{collection}] Progress: {idx}/{total} ({success} succeeded, {fail} failed)")

        logger.info(f"Finished upserting '{collection}' — {success} succeeded, {fail} failed.")

    def upsert_document(self, col: str, data: dict, doc_id: Optional[str] = None):
        """
        단일 문서를 Qdrant 컬렉션에 업서트합니다.
        - JSON 전체 해시 기반 db_id를 생성하여 중복 방지
        - Qdrant point ID는 항상 UUID 사용
        - 기존 id / parent_id는 payload에만 유지
        """
        trace(f"upsert_document({col}, id={doc_id})")

        try:
            # ① content 추출
            content = data.get("content") or data.get("contents") or ""

            # ② JSON 전체 해시 기반 db_id 생성
            normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)
            db_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            data["db_id"] = db_id  # payload에도 포함

            # ③ 벡터 생성
            dense_vec = self.dense_model.encode(content)
            bm25_vec = self.bm25_encode(content)
            splade_vec = self.splade_encode(content)
            bm25_sv = SparseVector(indices=list(bm25_vec.keys()), values=list(bm25_vec.values()))
            splade_sv = SparseVector(indices=list(splade_vec.keys()), values=list(splade_vec.values()))

            # ④ payload 구성
            payload = {
                **data,
                "id": data.get("id", doc_id),
                "parent_id": data.get("id", doc_id),
                "db_id": db_id
            }

            # ⑤ Qdrant에 업서트 (UUID 기반 ID)
            point_id = str(uuid.uuid4())

            self.client.upsert(
                collection_name=col,
                points=[
                    PointStruct(
                        id=point_id,  # 유효한 UUID
                        vector={
                            "dense": dense_vec,
                            "sparse": bm25_sv,
                            "splade": splade_sv
                        },
                        payload=payload
                    )
                ]
            )

            logger.info(f"[Upsert] {col}: db_id={db_id[:12]} inserted successfully (UUID={point_id})")

        except Exception as e:
            logger.error(f"[Upsert Error] db_id={db_id[:12]} in {col}: {e}")

    # ------------ Query ------------
        # ------------------------------------------------------
    # SEARCH (Dense/Sparse/SPLADE 각각 수행)
    # ------------------------------------------------------
    def _search_collection_unique(self, collection, query_text, top_k,
                                  use_dense, use_sparse, use_splade):
        trace(f"Searching unique docs from {collection}")
        dense_results, sparse_results, splade_results = [], [], []

        if use_dense:
            dense_vec = self.embedding_models["dense"].encode(query_text)
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
        
    def query(self, query_text: str, top_k: int = 10,
           collections: Optional[List[str]] = None, **kwargs) -> List[Dict[str, Any]]:
        trace(f"query('{query_text[:20]}...')")
        cfg = self.pipeline_config
        collections = collections or [self.default_collection]
        merged: List[Dict[str, Any]] = []

        # ==========================================================
        # (1) 각 컬렉션별 검색 및 통합
        # ==========================================================
        for col in collections:
            dense_res, sparse_res, splade_res = self._search_collection_unique(
                col, query_text, top_k,
                cfg["use_dense"], cfg["use_sparse"], cfg["use_splade"]
            )
            fused = weighted_fuse(
                dense_res, sparse_res, splade_res,
                cfg["dense_weight"], cfg["sparse_weight"], cfg["splade_weight"]
            )

            # deduplication 기준을 doc_id → db_id로 변경
            doclevel = dedup_avg_by_doc(
                fused, client=self.client, col_name=col, top_k=top_k
            )
            for d in doclevel:
                d["collection"] = col
            merged.extend(doclevel)

        merged.sort(key=lambda x: x["avg_score"], reverse=True)
        merged = merged[:top_k]
        logger.debug(f"Initial merged={len(merged)}")

        # ==========================================================
        # (2) Cross-Encoder 재정렬 (optional)
        # ==========================================================
        if cfg.get("use_reranker", True):
            logger.info("Applying cross-encoder reranker...")

            # (2-1) 모델 로드
            if self._cross_model is None or self._cross_model_name != cfg["cross_encoder_model"]:
                tok, mod = load_cross_encoder(cfg["cross_encoder_model"])
                self._cross_tokenizer, self._cross_model = tok, mod
                self._cross_model_name = cfg["cross_encoder_model"]

            candidates: List[Dict[str, Any]] = []
            id2meta: Dict[Any, Dict[str, Any]] = {}

            # ==========================================================
            # (2-2) Qdrant에서 payload 조회 (db_id 기준)
            # ==========================================================
            for d in merged:
                db_id = d.get("db_id") or d.get("id") or d.get("parent_id")
                col = d["collection"]
                if not db_id:
                    logger.debug("[CrossEncoder] skip: missing db_id")
                    continue

                p = None
                try:
                    # ✅ 1차: db_id 기반 직접 조회
                    fetched = self.client.retrieve(
                        collection_name=col,
                        ids=[db_id],
                        with_payload=True
                    )
                    if fetched:
                        p = fetched[0]
                    else:
                        # ✅ 2차 fallback: payload 내 parent_id나 id 검색
                        hits, _ = self.client.scroll(
                            collection_name=col,
                            scroll_filter=Filter(must=[
                                FieldCondition(key="parent_id", match=MatchValue(value=db_id))
                            ]),
                            limit=1,
                            with_payload=True
                        )
                        if hits:
                            p = hits[0]

                    if not p:
                        logger.debug(f"[CrossEncoder] No hits for db_id={db_id}")
                        continue

                    payload = p.payload or {}
                    text = (
                        payload.get("contents")
                        or payload.get("content")
                        or payload.get("text", "")
                    )
                    title = payload.get("title") or d.get("title") or "(no title)"

                    if not text.strip():
                        logger.debug(f"[CrossEncoder] empty text for db_id={db_id}, skip")
                        continue

                    candidates.append({
                        "id": db_id,
                        "text": text,
                        "title": title
                    })
                    id2meta[db_id] = {
                        "title": title,
                        "collection": col,
                        "avg_score": d.get("avg_score", 0.0),
                    }

                except Exception as e:
                    logger.warning(f"[CrossEncoder] fetch payload failed for db_id={db_id}: {e}")
                    continue

            if not candidates:
                logger.warning(f"[CrossEncoder] No candidates found for query='{query_text[:30]}...' — skipping reranking.")
                return merged

            # ==========================================================
            # (2-3) Rerank 실행
            # ==========================================================
            reranked = rerank_with_cross_encoder(
                query=query_text,
                docs=candidates,
                tokenizer=self._cross_tokenizer,
                model=self._cross_model,
                top_k=top_k,
                device="cpu",
            )
            logger.info(f"Cross-Encoder reranking done ({len(reranked)} results)")

            # ==========================================================
            # (2-4) Rerank 결과와 메타데이터 결합
            # ==========================================================
            final_after_ce: List[Dict[str, Any]] = []
            for r in reranked:
                meta = id2meta.get(r["id"], {})
                final_after_ce.append(
                    {
                        "db_id": r["id"],
                        "title": meta.get("title"),
                        "score": r.get("score", 0.0),
                        "collection": meta.get("collection", self.default_collection),
                        "avg_score": meta.get("avg_score", 0.0),
                    }
                )

            final_after_ce.sort(key=lambda x: x["score"], reverse=True)
            return final_after_ce[:top_k]

        # reranker 미사용 시
        return merged
        
        # ------------ Filter Search ------------
    def filter_search(self, col: str, filters: Dict[str, Any], limit: int = 10, with_vectors: bool = False):
        """
        Qdrant Filter 기반 문서 검색 (payload 조건만으로 검색)
        Dense/Sparse 벡터 계산 없이 메타데이터로만 필터링.

        Args:
            col (str): 컬렉션 이름
            filters (dict): key=value 형태의 조건 예) {"category": "AI", "verified": True}
            limit (int): 반환할 최대 문서 수
            with_vectors (bool): True면 벡터 포함, False면 payload만 반환

        Returns:
            List[dict]: 필터 조건에 맞는 문서 payload 리스트
        """
        trace(f"filter_search({col}, filters={filters})")
        try:
            # Qdrant 필터 구성
            must_conditions = []
            for k, v in filters.items():
                must_conditions.append(FieldCondition(key=k, match=MatchValue(value=v)))
            
            q_filter = Filter(must=must_conditions)

            # scroll 방식으로 안전하게 페이징 조회
            all_hits = []
            scroll_id = None
            while True:
                hits, scroll_id = self.client.scroll(
                    collection_name=col,
                    scroll_filter=q_filter,
                    limit=min(100, limit - len(all_hits)),
                    with_payload=True,
                    with_vectors=with_vectors
                )
                all_hits.extend(hits)
                if not scroll_id or len(all_hits) >= limit:
                    break

            results = []
            for h in all_hits[:limit]:
                results.append({
                    "id": h.id,
                    "payload": h.payload,
                    "score": getattr(h, "score", None)
                })

            logger.info(f"[FilterSearch] Found {len(results)} results in '{col}' matching {filters}")
            return results

        except Exception as e:
            logger.error(f"[FilterSearch] Error searching in {col}: {e}")
            return []
        
        # ------------ Update (Payload Only) ------------
    def update_payload(self, col: str, doc_id: str, new_payload: dict, merge: bool = True):
        """
        Qdrant 내 문서 payload(메타데이터)만 업데이트.
        벡터는 재계산하지 않음.

        Args:
            col (str): 대상 컬렉션 이름
            doc_id (str): 문서 ID (hash or original id)
            new_payload (dict): 새로 추가하거나 수정할 payload 값
            merge (bool): True면 기존 payload와 병합, False면 덮어씀
        """
        trace(f"update_payload({col}, id={doc_id}, merge={merge})")
        try:
            # 기존 payload 불러오기
            result = self.client.retrieve(
                collection_name=col, ids=[doc_id], with_payload=True
            )

            if not result:
                logger.warning(f"[UpdatePayload] Document not found in {col}: id={doc_id}")
                return False

            old_payload = result[0].payload or {}

            # merge 옵션에 따라 병합 혹은 덮어쓰기
            updated_payload = {**old_payload, **new_payload} if merge else new_payload

            # 실제 업데이트
            self.client.set_payload(
                collection_name=col,
                payload=updated_payload,
                points=[doc_id],
            )

            logger.info(f"[UpdatePayload] Updated payload for doc_id={doc_id} in '{col}'")
            return True

        except Exception as e:
            logger.error(f"[UpdatePayload] Error updating payload for id={doc_id}: {e}")
            return False
        
        # ------------ Delete ------------
    from qdrant_client.models import PointIdsList

    def delete_document(self, col: str, db_id: str) -> bool:
        """
        지정한 문서 db_id를 Qdrant 컬렉션에서 삭제.

        Args:
            col (str): 컬렉션 이름
            db_id (str): 삭제할 문서의 SHA-256 기반 고유 ID
        Returns:
            bool: 삭제 성공 여부
        """
        trace(f"delete_document({col}, db_id={db_id[:12]}...)")
        try:
            # Qdrant에서는 PointIdsList 객체를 명시적으로 전달해야 함
            self.client.delete(
                collection_name=col,
                points_selector=PointIdsList(points=[db_id])
            )
            logger.info(f"[Delete] Deleted db_id={db_id[:12]}... from '{col}'")
            return True

        except Exception as e:
            logger.error(f"[Delete] Error deleting db_id={db_id[:12]}... from '{col}': {e}")
            return False


    def delete_by_filter(self, col: str, field: str, value: Any) -> int:
        """
        특정 필드 값 기준으로 문서 일괄 삭제.
        예: delete_by_filter("notion.marketing", "category", "AI")

        Args:
            col (str): 컬렉션 이름
            field (str): 필드명 (예: "category")
            value (Any): 일치 조건 값
        Returns:
            int: 삭제된 문서 개수 (성공 시)
        """
        trace(f"delete_by_filter({col}, field={field}, value={value})")
        try:
            condition = Filter(
                must=[FieldCondition(key=field, match=MatchValue(value=value))]
            )

            result = self.client.delete(
                collection_name=col,
                points_selector=condition
            )

            deleted_count = getattr(result, "result", {}).get("num_points", 0)
            logger.info(f"[DeleteByFilter] Deleted {deleted_count} docs from '{col}' where {field}={value}")
            return deleted_count

        except Exception as e:
            logger.error(f"[DeleteByFilter] Error deleting docs from {col}: {e}")
            return 0
        
    def auto_initialize(self, base_folder="./data", snapshot_dir="./snapshots"):
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
            reverse=True
        )

        if snapshots:
            latest = snapshots[0]
            logger.info(f"[Init] Found snapshot: {latest} — restoring...")
            self.restore_snapshot(self.default_collection, os.path.join(snapshot_dir, latest))
        else:
            logger.warning("[Init] No snapshot found — creating collection from local data")
            self.create_collection(self.default_collection, vector_size=768)
            self.init_bm25(base_path=base_folder)
            self.upsert_folder(os.path.join(base_folder, "notion/marketing"), self.default_collection)
            self.create_snapshot(self.default_collection, snapshot_dir)

    # ------------ 로깅 ------------
    def log_results(self, results: List[Dict[str, Any]], title="Results", top_n=10):
        logger.info(f"=== {title} ===")
        if not results:
            logger.warning("No results to display.")
            return

        for i, r in enumerate(results[:top_n], 1):
            rid = r.get("id") or r.get("doc_id") or "unknown_id"
            scr = r.get("final_score") or r.get("score") or r.get("avg_score") or 0.0
            t = r.get("title") or r.get("text") or r.get("content") or ""
            col = r.get("collection", self.default_collection)

            # 문자열 아닌 값 대비 (예: NoneType 방지)
            if not isinstance(t, str):
                t = str(t) if t is not None else ""

            logger.info(f"{i:02d}. {col} | {rid} | {t[:30]} | score={scr:.4f}")

        logger.info("===================================\n")