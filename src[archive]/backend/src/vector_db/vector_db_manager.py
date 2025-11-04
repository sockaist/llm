# vector_db_manager.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import math
from typing import Any, Dict, List, Optional, Tuple
from tqdm import tqdm
import warnings
import hashlib
warnings.filterwarnings("ignore", message="BertForMaskedLM has generative capabilities")

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    NamedVector,
    FilterSelector,
    SparseVector,
)

from qdrant_client.http.models import ScoredPoint

# ---- 외부 모듈(이미 주어진 코드들) ----
from config import QDRANT_URL, QDRANT_API_KEY, DISTANCE, FORMATS
from embedding import model as dense_sbert_model
from embedding import content_embedder
from sparse_helper import bm25_encode, bm25_fit
from splade_module import splade_encode
from vector_db_helper import (
    create_doc_upsert,
    query_unique_docs as qdrant_query_unique_docs,
)
from reranker_module import (
    weighted_fuse,
    deduplicate_and_average as dedup_avg_by_doc,
    load_cross_encoder,
    rerank_with_cross_encoder,
    apply_date_window_boost,  # 날짜 부스팅(단일 컬렉션 버전)
)

# -------------------------------------------------------
# VectorDBManager
# -------------------------------------------------------
class VectorDBManager:
    """
    Qdrant 기반 멀티 컬렉션 벡터 DB 매니저
    - Create: 컬렉션 생성/초기화
    - Read: 하이브리드 검색 (Dense + BM25 + SPLADE) → 가중 결합 → (옵션)Cross-Encoder → (옵션)Date-Boost
    - Update: 문서 업데이트(재임베딩 옵션)
    - Delete: 문서 삭제
    """

    # ------------ 초기화 ------------
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_collection: Optional[str] = None,
        pipeline_config: Optional[Dict[str, Any]] = None,
    ):
        self.client = QdrantClient(
            url=url or QDRANT_URL, api_key=api_key or QDRANT_API_KEY
        )
        self.default_collection = default_collection or "notion.marketing"

        # 임베딩 모델 핸들
        self.embedding_models: Dict[str, Any] = {
            "dense": dense_sbert_model,  # SentenceTransformer
            # sparse(BM25)와 splade는 함수형 인코더를 그대로 사용
        }

        # Cross-Encoder (필요 시 지연 초기화)
        self._cross_tokenizer = None
        self._cross_model = None
        self._cross_model_name = None
        from sparse_helper import bm25_encode
        from splade_module import splade_encode

        self.dense_model = dense_sbert_model
        self.bm25_encode = bm25_encode
        self.splade_encode = splade_encode

        # 파이프라인 설정 기본값
        self.pipeline_config: Dict[str, Any] = {
            "use_dense": True,
            "use_sparse": True,
            "use_splade": True,
            "use_reranker": True,
            "use_date_boost": True,
            "dense_weight": 0.6,
            "sparse_weight": 0.3,
            "splade_weight": 0.1,
            "cross_encoder_model": "Dongjin-kr/ko-reranker",
            # Date boost 기본 파라미터
            "date_decay_rate": 0.03,
            "date_weight": 0.45,
            # 날짜 윈도우(옵션): 문자열 ISO8601 또는 None
            "date_from": None,
            "date_to": None,
        }
        if pipeline_config:
            self.pipeline_config.update(pipeline_config)

    # ------------ Create / Init ------------
    def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: str | Distance = "Cosine",
        force: bool = False,
        include_sparse: bool = True,
        include_splade: bool = True,
    ) -> Dict[str, Any]:
        """
        Qdrant에 멀티-벡터 스키마로 컬렉션 생성 (dense + sparse + splade)
        """
        if isinstance(distance, str):
            distance = {
                "Cosine": Distance.COSINE,
                "Dot": Distance.DOT,
                "Euclid": Distance.EUCLID,
            }.get(distance, Distance.COSINE)

        if force:
            try:
                self.client.delete_collection(name)
            except Exception:
                pass

        vectors_cfg = {"dense": VectorParams(size=vector_size, distance=distance)}
        sparse_cfg = {}
        if include_sparse:
            sparse_cfg["sparse"] = SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            )
        if include_splade:
            sparse_cfg["splade"] = SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            )

        self.client.recreate_collection(
            collection_name=name,
            vectors_config=vectors_cfg,
            sparse_vectors_config=sparse_cfg if sparse_cfg else None,
        )
        return {"name": name, "vector_size": vector_size, "distance": str(distance)}

    def initialize_collections(self, config: Dict[str, Dict[str, Any]]) -> None:
        """
        여러 컬렉션을 한 번에 초기화
        Example:
        {
            "notion.marketing": {"vector_size": 768, "distance": "Cosine"},
            "notion.notice": {"vector_size": 768, "distance": "Cosine"}
        }
        """
        for col_name, spec in config.items():
            self.create_collection(
                name=col_name,
                vector_size=spec.get("vector_size", 768),
                distance=spec.get("distance", "Cosine"),
                force=spec.get("force", False),
                include_sparse=True,
                include_splade=True,
            )

    # ------------ BM25 학습 헬퍼 ------------
    def fit_bm25_from_json_folder(self, base_path: str) -> int:
        """
        폴더 내 모든 JSON에서 content/contents를 모아 BM25 벡터라이저 학습
        """
        import json

        all_texts: List[str] = []
        for root, _, files in os.walk(base_path):
            for file in files:
                if not file.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        text = data.get("content") or data.get("contents")
                        if text:
                            all_texts.append(text)
                except Exception:
                    continue

        if not all_texts:
            raise RuntimeError("[BM25] No text data found for fitting")
        bm25_fit(all_texts)
        return len(all_texts)

    # ------------ Upsert / Update / Delete ------------
    def make_doc_hash_id(self, file_path: str):
        """
        파일의 상대경로를 해시해서 Qdrant 고유 ID 생성
        (절대경로가 달라도 동일 폴더 구조면 같은 결과를 보장)
        """
        rel_path = os.path.relpath(file_path, start=os.getcwd())
        return hashlib.md5(rel_path.encode("utf-8")).hexdigest()

    def upsert_folder(self, folder_path: str, collection_name: str):
        """
        폴더 내 모든 JSON 문서를 읽어 자동으로 벡터 생성 후 업서트
        """
        import os, json
        from tqdm import tqdm

        if not os.path.exists(folder_path):
            print(f"Folder not found: {folder_path}")
            return

        files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
        if not files:
            print(f"No JSON files in {folder_path}")
            return

        print(f"Upserting data from: {folder_path}")
        print(f"[INFO] Upserting {len(files)} documents into {collection_name}")

        for file_name in tqdm(files, desc=f"Upserting → {collection_name}"):
            file_path = os.path.join(folder_path, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                doc_id = self.make_doc_hash_id(file_path)
                self.upsert_document(collection_name, data, doc_id)
            except Exception as e:
                print(f"[ERROR] Failed to upsert {file_name}: {e}")

    def upsert_document(self, collection_name, data, doc_id):
        """
        단일 문서를 Qdrant에 업서트합니다.
        - content(또는 contents) 필드로부터 Dense, BM25, SPLADE 벡터를 자동 생성
        - 모든 벡터는 NamedVector로 저장됨
        """
        from qdrant_client.models import PointStruct, SparseVector

        content = data.get("content") or data.get("contents") or ""
        title = data.get("title", "")

        # Dense embedding (SentenceTransformer)
        dense_vec = self.dense_model.encode(content)

        # Sparse embeddings
        bm25_vec = self.bm25_encode(content)
        splade_vec = self.splade_encode(content)

        # BM25, SPLADE이 dict이면 SparseVector로 변환
        if isinstance(bm25_vec, dict):
            bm25_vec = SparseVector(
                indices=list(bm25_vec.keys()),
                values=list(bm25_vec.values())
            )
        if isinstance(splade_vec, dict):
            splade_vec = SparseVector(
                indices=list(splade_vec.keys()),
                values=list(splade_vec.values())
            )

        # 문서 원본 경로 / id 추가
        payload = {
            **data,
            "title": title,
            "id": doc_id,
            "parent_id": doc_id
        }

        # Qdrant 업서트
        self.client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=doc_id,
                    vector={
                        "dense": dense_vec,
                        "sparse": bm25_vec,
                        "splade": splade_vec
                    },
                    payload=payload
                )
            ]
        )

    def delete_document(self, collection: str, doc_id: Any) -> bool:
        """
        문서 삭제:
        - parent_id==doc_id 조건으로 모든 청크 삭제
        """
        try:
            self.client.delete(
                collection_name=collection,
                points_selector=FilterSelector(
                    filter=Filter(must=[FieldCondition(key="parent_id", match=MatchValue(value=doc_id))])
                ),
            )
            return True
        except Exception:
            return False

    # ------------ 조회 유틸 ------------
    def get_document_by_id(self, collection: str, doc_id: Any) -> Optional[Dict[str, Any]]:
        """
        parent_id == doc_id인 첫 포인트의 payload를 대표로 반환
        """
        hits, _ = self.client.scroll(
            collection_name=collection,
            scroll_filter=Filter(must=[FieldCondition(key="parent_id", match=MatchValue(value=doc_id))]),
            limit=1,
            with_payload=True,
        )
        if not hits:
            return None
        p = hits[0]
        return {"id": doc_id, "payload": p.payload}

    def get_top_documents(self, results: List[Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        return results[:top_n]

    # ------------ 내부: 컬렉션 단위 검색 ------------
    def _search_collection_unique(
        self,
        collection: str,
        query_text: str,
        top_k: int,
        use_dense: bool,
        use_sparse: bool,
        use_splade: bool,
    ) -> Tuple[List[ScoredPoint], List[ScoredPoint], List[ScoredPoint]]:
        """
        한 컬렉션에 대해 Dense/BM25/SPLADE로 고유 문서 top_k를 각각 가져옴
        """
        dense_results: List[ScoredPoint] = []
        sparse_results: List[ScoredPoint] = []
        splade_results: List[ScoredPoint] = []

        # Dense
        if use_dense:
            dense_vec = self.embedding_models["dense"].encode(query_text)
            dense_results = qdrant_query_unique_docs(
                client=self.client,
                collection_name=collection,
                query=dense_vec,
                using="dense",
                top_k=top_k,
            )

        # BM25
        if use_sparse:
            bm25_vec = bm25_encode(query_text)
            if isinstance(bm25_vec, dict):
                bm25_vec = SparseVector(
                    indices=list(bm25_vec.keys()), values=list(bm25_vec.values())
                )
            sparse_results = qdrant_query_unique_docs(
                client=self.client,
                collection_name=collection,
                query=bm25_vec,
                using="sparse",
                top_k=top_k,
            )

        # SPLADE
        if use_splade:
            sp_vec = splade_encode(query_text)
            if isinstance(sp_vec, dict):
                # splade_module은 key가 str일 수 있으니 int 변환
                idxs = [int(k) for k in sp_vec.keys()]
                vals = [float(v) for v in sp_vec.values()]
                sp_vec = SparseVector(indices=idxs, values=vals)
            splade_results = qdrant_query_unique_docs(
                client=self.client,
                collection_name=collection,
                query=sp_vec,
                using="splade",
                top_k=top_k,
            )

        return dense_results, sparse_results, splade_results

    # ------------ 핵심: Query 파이프라인 ------------
    def query(
        self,
        query_text: str,
        top_k: int = 10,
        collections: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        use_reranker: Optional[bool] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        date_decay_rate: Optional[float] = None,
        date_weight: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query → Dense/Sparse/SPLADE → 가중 결합 → 문서 단위 평균/Dedup
              → (옵션) Cross-Encoder → (옵션) Date-Boost → 결과
        """
        cfg = self.pipeline_config
        use_dense = cfg["use_dense"]
        use_sparse = cfg["use_sparse"]
        use_splade = cfg["use_splade"]
        use_reranker = cfg["use_reranker"] if use_reranker is None else use_reranker
        use_date_boost = cfg["use_date_boost"]

        dw = (cfg["dense_weight"], cfg["sparse_weight"], cfg["splade_weight"])

        collections = collections or [self.default_collection]
        merged_doclevel: List[Dict[str, Any]] = []

        for col in collections:
            dense_res, sparse_res, splade_res = self._search_collection_unique(
                collection=col,
                query_text=query_text,
                top_k=top_k,
                use_dense=use_dense,
                use_sparse=use_sparse,
                use_splade=use_splade,
            )

            # 모델별 결과 결합(점수 정규화 + 가중합)
            fused = weighted_fuse(
                dense_res, sparse_res, splade_res, dw[0], dw[1], dw[2]
            )

            # 문서 단위 평균점수 + Dedup
            doclevel = dedup_avg_by_doc(fused, client=self.client, col_name=col, top_k=top_k)
            # 컬렉션명 부착
            for d in doclevel:
                d["collection"] = col

            merged_doclevel.extend(doclevel)

        # 여러 컬렉션을 합쳤다면 단순 상위 top_k로 자르기
        merged_doclevel.sort(key=lambda x: x["avg_score"], reverse=True)
        merged_doclevel = merged_doclevel[:top_k]

        # ---- (옵션) Cross-Encoder ----
        if use_reranker:
            # Cross Encoder 모델 로드(지연 로딩)
            if self._cross_model is None or self._cross_model_name != cfg["cross_encoder_model"]:
                tok, mod = load_cross_encoder(cfg["cross_encoder_model"])
                self._cross_tokenizer, self._cross_model = tok, mod
                self._cross_model_name = cfg["cross_encoder_model"]

            # 각 문서에서 대표 청크 1개를 뽑아 candidate 구성
            candidates: List[Dict[str, Any]] = []
            id2meta: Dict[Any, Dict[str, Any]] = {}
            for d in merged_doclevel:
                doc_id = d["doc_id"]
                col = d["collection"]
                hits, _ = self.client.scroll(
                    collection_name=col,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="parent_id", match=MatchValue(value=doc_id))]
                    ),
                    limit=1,
                )
                if not hits:
                    continue
                p = hits[0]
                text = p.payload.get("contents") or p.payload.get("content") or p.payload.get("text", "")
                title = p.payload.get("title") or d.get("title", "(no title)")
                candidates.append({"id": doc_id, "text": text, "title": title})
                id2meta[doc_id] = {
                    "title": title,
                    "collection": col,
                    "avg_score": d.get("avg_score", 0.0),
                }
            
            if not candidates:
                print("[WARN] No candidates found for reranking — skipping Cross-Encoder.")
                return merged_doclevel[:top_k]

            reranked = rerank_with_cross_encoder(
                query=query_text,
                docs=candidates,
                tokenizer=self._cross_tokenizer,
                model=self._cross_model,
                top_k=top_k,
                device="cpu",
            )
            # Cross 결과에 컬렉션, 평균점수 등 메타 합치기
            final_after_ce: List[Dict[str, Any]] = []
            for r in reranked:
                meta = id2meta.get(r["id"], {})
                final_after_ce.append(
                    {
                        "id": r["id"],
                        "title": r.get("title"),
                        "score": r.get("score", 0.0),
                        "collection": meta.get("collection", self.default_collection),
                        "avg_score": meta.get("avg_score", 0.0),
                    }
                )
        else:
            # Cross-Encoder 미사용 시, avg_score 기반 결과를 그대로 사용
            final_after_ce = [
                {
                    "id": d["doc_id"],
                    "title": d.get("title"),
                    "score": float(d.get("avg_score", 0.0)),  # 'score' 슬롯에 avg_score 투입
                    "collection": d["collection"],
                    "avg_score": float(d.get("avg_score", 0.0)),
                }
                for d in merged_doclevel
            ]

        # ---- (옵션) Date-Boost ----
        if use_date_boost:
            # 요청 인자 우선, 없으면 cfg 사용
            df = date_from if date_from is not None else cfg.get("date_from")
            dt = date_to if date_to is not None else cfg.get("date_to")
            decay = date_decay_rate if date_decay_rate is not None else cfg.get("date_decay_rate", 0.03)
            w = date_weight if date_weight is not None else cfg.get("date_weight", 0.45)

            # 여러 컬렉션 섞여있으면 컬렉션별로 날짜부스팅 적용 후 합치기
            by_col: Dict[str, List[Dict[str, Any]]] = {}
            for r in final_after_ce:
                by_col.setdefault(r["collection"], []).append(r)

            boosted_merged: List[Dict[str, Any]] = []
            for col, subset in by_col.items():
                boosted = apply_date_window_boost(
                    results=subset,
                    client=self.client,
                    collection_name=col,
                    date_from=df,
                    date_to=dt,
                    decay_rate=decay,
                    weight=w,
                )
                boosted_merged.extend(boosted)

            boosted_merged.sort(key=lambda x: x["final_score"], reverse=True)
            return boosted_merged[:top_k]
        
        # --- threshold 적용 ---
        if threshold is not None:
            # CrossEncoder 사용 시: 'score' 또는 'final_score'를 기준으로 필터링
            key_field = "final_score" if use_date_boost else "score"
            before = len(merged_doclevel)
            merged_doclevel = [r for r in merged_doclevel if float(r.get(key_field, 0)) >= threshold]
            after = len(merged_doclevel)
            print(f"[INFO] Threshold {threshold} applied ({before} → {after} results)")

        # 날짜 부스팅 비활성: Cross 결과 그대로
        # 정규화 없이 score 내림차순
        final_after_ce.sort(key=lambda x: x["score"], reverse=True)
        return final_after_ce[:top_k]

    # ------------ 키워드 검색(간단 BM25 대용) ------------
    def keyword_search(
        self,
        keyword: str,
        collections: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Qdrant의 payload 필드 직접 '부분 문자열 검색'은 지원되지 않으므로,
        BM25(Sparse) 쿼리로 키워드 검색을 근사한다.
        """
        collections = collections or [self.default_collection]
        results: List[Dict[str, Any]] = []

        bm25_vec = bm25_encode(keyword)
        spv = SparseVector(indices=list(bm25_vec.keys()), values=list(bm25_vec.values()))

        for col in collections:
            hits = self.client.query_points(
                collection_name=col, query=spv, using="sparse", limit=limit
            )
            points = hits.points if hasattr(hits, "points") else hits
            for p in points:
                pid = getattr(p, "id", None)
                title = p.payload.get("title")
                results.append(
                    {
                        "id": pid,
                        "title": title,
                        "score": float(p.score),
                        "collection": col,
                    }
                )

        # 점수 내림차순
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # ------------ Reranker 단독 실행 ------------
    def rerank_results(
        self,
        query_text: str,
        docs: List[Dict[str, Any]],
        method: str = "cross_encoder",
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        전달된 docs(list of {id,title,text})를 주어진 방법으로 재정렬
        """
        if method == "average":
            # 단순 평균점수로 이미 계산되어 있다고 가정 → 정렬만
            docs.sort(key=lambda x: x.get("avg_score", 0.0), reverse=True)
            return docs[:top_k]

        if method == "cross_encoder":
            if self._cross_model is None or self._cross_model_name != self.pipeline_config["cross_encoder_model"]:
                tok, mod = load_cross_encoder(self.pipeline_config["cross_encoder_model"])
                self._cross_tokenizer, self._cross_model = tok, mod
                self._cross_model_name = self.pipeline_config["cross_encoder_model"]

            reranked = rerank_with_cross_encoder(
                query=query_text,
                docs=docs,
                tokenizer=self._cross_tokenizer,
                model=self._cross_model,
                top_k=top_k,
                device="cpu",
            )
            return reranked

        if method == "ensemble":
            # 추후 MonoT5 등 추가시 확장 포인트
            raise NotImplementedError("Ensemble reranker is not implemented yet.")

        raise ValueError(f"Unknown reranker method: {method}")

    # ------------ 날짜 부스팅(래퍼) ------------
    def apply_date_boost(
        self,
        results: List[Dict[str, Any]],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        decay_rate: Optional[float] = None,
        weight: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        여러 컬렉션이 섞일 수 있으므로, collection별 그룹핑 후 모듈 함수를 호출
        """
        df = date_from or self.pipeline_config.get("date_from")
        dt = date_to or self.pipeline_config.get("date_to")
        decay = decay_rate if decay_rate is not None else self.pipeline_config.get("date_decay_rate", 0.03)
        w = weight if weight is not None else self.pipeline_config.get("date_weight", 0.45)

        by_col: Dict[str, List[Dict[str, Any]]] = {}
        for r in results:
            col = r.get("collection", self.default_collection)
            by_col.setdefault(col, []).append(r)

        boosted_merged: List[Dict[str, Any]] = []
        for col, subset in by_col.items():
            boosted = apply_date_window_boost(
                results=subset,
                client=self.client,
                collection_name=col,
                date_from=df,
                date_to=dt,
                decay_rate=decay,
                weight=w,
            )
            boosted_merged.extend(boosted)

        boosted_merged.sort(key=lambda x: x["final_score"], reverse=True)
        return boosted_merged

    # ------------ 로깅 ------------
    def log_results(
        self, results: List[Dict[str, Any]], title: str = "Results", top_n: int = 10
    ) -> None:
        print(f"\n=== {title} ===")
        for i, r in enumerate(results[:top_n], 1):
            rid = r.get("id") or r.get("doc_id")
            scr = r.get("final_score") or r.get("score") or r.get("avg_score")
            t = r.get("title")
            dt = r.get("date")
            fresh = r.get("freshness")
            col = r.get("collection", self.default_collection)
            score_fmt = f"{scr:.4f}" if isinstance(scr, (int, float)) else "0.0000"
            print(f"{i:02d}. ID={rid}, Score={score_fmt}, "
                  f"Fresh={fresh:.3f}, Date={dt}, Title={t}, Col={col}")
        print("===================================\n")


# -------------------------------------------------------
# 빠른 수동 테스트 (원하면 주석 해제)
# -------------------------------------------------------
if __name__ == "__main__":
    # 1) 매니저 초기화
    mgr = VectorDBManager(default_collection="notion.marketing")

    # 2) (선택) BM25 학습 — JSON 루트 경로 지정
    #    mgr.fit_bm25_from_json_folder("../../../../data")

    # 3) (선택) 컬렉션 생성
    # mgr.create_collection("notion.marketing", vector_size=768, distance="Cosine", force=False)

    # 4) 질의
    query = "인턴 모집 일정"
    results = mgr.query(
        query_text=query,
        top_k=10,
        collections=["notion.marketing"],  # 여러 개 가능
        use_reranker=True,
        # 날짜 윈도우를 강제로 지정하고 싶으면 아래 값 사용(없으면 pipeline_config를 따름)
        date_from="2025-10-01T00:00:00Z",
        date_to="2025-10-03T23:59:59Z",
        date_decay_rate=0.03,
        date_weight=0.45,
    )
    mgr.log_results(results, title=f"FINAL for '{query}'", top_n=10)