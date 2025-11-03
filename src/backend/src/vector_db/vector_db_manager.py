# vector_db_manager.py

from __future__ import annotations
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
import os
import json

from qdrant_client import QdrantClient, models
from qdrant_client.models import NamedVector, PointStruct, PointIdsList, Filter, FieldCondition, MatchValue, SparseVector
from sentence_transformers import SentenceTransformer

# 재사용: 기존 모듈 그대로 활용
from config import FORMATS, QDRANT_URL, QDRANT_API_KEY
from init import auto_recreate_collections
from embedding import content_embedder
from sparse_helper import bm25_fit, bm25_encode
from splade_module import splade_encode
from reranker_module import combine_scores, print_rerank_summary


def _to_sparse_vector(vec_like: Dict[Any, float]) -> SparseVector:
    """
    Qdrant SparseVector로 변환 (key가 int/str 섞여도 안전 변환)
    """
    if not vec_like:
        return SparseVector(indices=[], values=[])
    # dict 키가 str인 경우도 있고 int인 경우도 있어 통일
    items = [(int(k), float(v)) for k, v in vec_like.items()]
    items.sort(key=lambda x: x[0])
    indices = [i for i, _ in items]
    values = [v for _, v in items]
    return SparseVector(indices=indices, values=values)


class VectorDBManager:
    """
    Qdrant 기반 문서 벡터 DB 매니저

    기능:
      - 스키마 자동 보장 (dense + sparse + splade)
      - DB 초기화 (BM25 학습 + 대량 업서트)
      - 단일 문서 업서트/업데이트/삭제/조회
      - 하이브리드 검색(dense + BM25 + SPLADE) + 날짜 가중 + 리랭킹
    """

    def __init__(
        self,
        client: Optional[QdrantClient] = None,
        dense_model: Optional[SentenceTransformer] = None,
        qdrant_url: Optional[str] = None,
        api_key: Optional[str] = None,
        dense_model_name: str = "jhgan/ko-sroberta-multitask",
    ):
        self.client = client or QdrantClient(url=qdrant_url or QDRANT_URL, api_key=api_key or QDRANT_API_KEY)
        self.dense_model = dense_model or SentenceTransformer(dense_model_name)

    # -------------------------
    # 컬렉션/DB 초기화
    # -------------------------
    def ensure_schema(self, collections: Optional[List[str]] = None) -> None:
        """
        컬렉션 스키마(dense + sparse + splade) 없거나 틀리면 삭제 후 재생성
        """
        auto_recreate_collections(self.client if collections is None else self.client)

    def fit_bm25_from_folder(self, base_path: str) -> int:
        """
        폴더 내 모든 .json의 'content/contents'를 모아 BM25 학습
        """
        all_texts: List[str] = []
        for root, _, files in os.walk(base_path):
            for file in files:
                if not file.endswith(".json"):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    text = data.get("content") or data.get("contents")
                    if text:
                        all_texts.append(text)
                except Exception:
                    continue

        if all_texts:
            bm25_fit(all_texts)
        return len(all_texts)

    def initialize_db(self, base_path: str, folders: Optional[List[str]] = None) -> None:
        """
        1) 스키마 보장 → 2) BM25 학습 → 3) 대량 업서트
        """
        # 1) 스키마
        self.ensure_schema()

        # 2) BM25 학습
        n = self.fit_bm25_from_folder(base_path)
        print(f"BM25 fitted on {n} documents.")

        # 3) 대량 업서트 (FORMATS 키 사용)
        targets = folders or list(FORMATS.keys())
        for col_name in targets:
            folder = col_name.replace(".", "/")
            folder_path = os.path.join(base_path, folder)
            self.bulk_upsert_folder(folder_path, col_name)

    # -------------------------
    # 업서트/업데이트/삭제/조회
    # -------------------------
    def upsert_document(self, col_name: str, data: dict) -> None:
        """
        단일 문서 업서트: 청킹 → dense/bm25/splade 생성 → 업서트
        기존 vector_db_helper.create_doc_upsert와 동일 로직 유지
        """
        # 필수 필드 검사
        doc_id = data.get("id")
        raw_text = (data.get("content") or data.get("contents") or "").strip()
        if not doc_id or not raw_text:
            print(f"[Skip] Missing id or empty content for {col_name}")
            return

        # 중복 확인
        exist = self.client.count(
            collection_name=col_name,
            count_filter=models.Filter(
                must=[models.FieldCondition(key="id", match=models.MatchValue(value=doc_id))]
            ),
            exact=False,
        ).count > 0
        if exist:
            print(f"[Skip] Document id={doc_id} already exists in {col_name}")
            return

        # 임베딩
        dense_vec = self.dense_model.encode(raw_text)
        if hasattr(dense_vec, "tolist"):
            dense_vec = dense_vec.tolist()

        bm25_dict = bm25_encode(raw_text)
        splade_dict = splade_encode(raw_text)
        bm25_sv = _to_sparse_vector(bm25_dict)
        splade_sv = _to_sparse_vector(splade_dict)

        # 청킹
        chunks = content_embedder(raw_text)
        if not chunks:
            print(f"[Skip] No chunks generated for id={doc_id}")
            return

        # 새 포인트 ID 부여
        base_id = self.client.count(collection_name=col_name, exact=True).count + 1
        points: List[PointStruct] = []

        for i, (chunk_text, _) in enumerate(chunks):
            payload = {"text": chunk_text, "parent_id": doc_id}
            # FORMATS에 정의된 필드 동기화
            if col_name in FORMATS:
                for key in FORMATS[col_name]:
                    payload[key] = data.get(key, "")

            points.append(PointStruct(
                id=base_id + i,
                vector={"dense": dense_vec, "sparse": bm25_sv, "splade": splade_sv},
                payload=payload
            ))

        self.client.upsert(collection_name=col_name, points=points)
        print(f"[Upsert] id={doc_id} → {col_name} (chunks={len(points)})")

    def bulk_upsert_folder(self, folder_path: str, col_name: str, n: int = 0) -> None:
        """
        폴더 내 모든 JSON 업서트 (기존 vector_db_helper.upsert_folder와 호환)
        """
        if not os.path.exists(folder_path):
            print(f"[Skip] Folder not found: {folder_path}")
            return

        files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
        if not files:
            print(f"[Skip] No JSON files in {folder_path}")
            return

        ok, fail = 0, 0
        for i, filename in enumerate(files):
            if n and i >= n:
                break
            path = os.path.join(folder_path, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # id 인덱스(없으면) 생성
                try:
                    self.client.create_payload_index(
                        collection_name=col_name,
                        field_name="id",
                        field_schema=models.PayloadSchemaType.INTEGER,
                        wait=True,
                    )
                except Exception:
                    pass
                self.upsert_document(col_name, data)
                ok += 1
            except Exception as e:
                print(f"[Error] {filename}: {e}")
                fail += 1

        print(f"[BulkUpsert] {col_name}: {ok} succeeded, {fail} failed")

    def _collect_point_ids_by_parent(self, col_name: str, doc_id: int) -> List[int]:
        """
        payload.parent_id == doc_id인 포인트 id 수집
        """
        point_ids: List[int] = []
        offset = None
        flt = Filter(must=[FieldCondition(key="parent_id", match=MatchValue(value=doc_id))])

        while True:
            scroll_res, next_page = self.client.scroll(
                collection_name=col_name,
                scroll_filter=flt,
                with_payload=False,
                with_vectors=False,
                offset=offset,
                limit=256,
            )
            for pt in scroll_res:
                point_ids.append(pt.id)
            if not next_page:
                break
            offset = next_page
        return point_ids

    def update_document(self, col_name: str, data: dict) -> None:
        """
        문서 전체 업데이트: 기존 parent_id 묶음 삭제 → 새로 업서트
        (기존 update_doc가 단일 dense만 다루던 점을 보완)
        """
        doc_id = data.get("id")
        if doc_id is None:
            print("[Skip] update_document requires 'id'")
            return

        # 기존 포인트 삭제
        ids = self._collect_point_ids_by_parent(col_name, doc_id)
        if ids:
            self.client.delete(collection_name=col_name, points_selector=PointIdsList(points=ids))
            print(f"[Delete] {col_name} parent_id={doc_id} (points={len(ids)})")

        # 재업서트
        self.upsert_document(col_name, data)

    def delete_document(self, col_name: str, doc_id: int) -> None:
        """
        문서 삭제: parent_id 기반으로 전체 포인트 삭제
        """
        ids = self._collect_point_ids_by_parent(col_name, doc_id)
        if not ids:
            print(f"[Delete] No points found for parent_id={doc_id} in {col_name}")
            return
        self.client.delete(collection_name=col_name, points_selector=PointIdsList(points=ids))
        print(f"[Delete] {col_name} parent_id={doc_id} (points={len(ids)})")

    def get_document_head(self, col_name: str, doc_id: int) -> Optional[dict]:
        """
        해당 문서(parent_id)의 첫 청크 payload 반환 (제목/날짜 확인용)
        """
        flt = Filter(must=[FieldCondition(key="parent_id", match=MatchValue(value=doc_id))])
        pts, _ = self.client.scroll(
            collection_name=col_name,
            scroll_filter=flt,
            with_payload=True,
            with_vectors=False,
            limit=1,
        )
        if pts:
            return pts[0].payload
        return None

    # -------------------------
    # 검색 + 리랭킹 + 날짜 가중
    # -------------------------
    def _apply_date_weight(
        self,
        ranked: List[Tuple[int, float]],
        col_name: str,
        start_date: Optional[str],
        end_date: Optional[str],
        date_weight: float,
    ) -> List[Tuple[int, float]]:
        if not start_date or not end_date:
            return ranked

        try:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except Exception:
            return ranked

        span = max((end - start).days, 1)
        adjusted: List[Tuple[int, float]] = []

        for pid, base_score in ranked:
            doc = self.client.retrieve(collection_name=col_name, ids=[pid], with_payload=True)
            if not doc:
                adjusted.append((pid, base_score))
                continue
            payload = doc[0].payload or {}
            date_str = payload.get("date")
            if not date_str:
                adjusted.append((pid, base_score))
                continue
            try:
                d = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                if start <= d <= end:
                    factor = 1.0
                else:
                    diff = min(abs((d - start).days), abs((d - end).days))
                    factor = max(0.5, 1 - diff / span)
                adjusted.append((pid, base_score * (1 + date_weight * factor)))
            except Exception:
                adjusted.append((pid, base_score))
        adjusted.sort(key=lambda x: x[1], reverse=True)
        return adjusted

    def search(
        self,
        col_name: str,
        query: str,
        top_k: int = 20,
        w_dense: float = 0.6,
        w_sparse: float = 0.25,
        w_splade: float = 0.15,
        start_date: Optional[str] = None,  # "2024-05-01"
        end_date: Optional[str] = None,    # "2024-06-01"
        date_weight: float = 0.0,          # 0이면 비활성
        print_summary: bool = True,
        summary_top_n: int = 10,
    ) -> List[Tuple[int, float]]:
        """
        하이브리드 검색(dense + BM25 + SPLADE) → 점수 결합 → (옵션) 날짜 가중 → rerank 결과 반환
        """
        # 1) 쿼리 벡터 준비
        dense_q = self.dense_model.encode(query)
        bm25_q = _to_sparse_vector(bm25_encode(query))
        splade_q = _to_sparse_vector(splade_encode(query))

        # 2) 개별 검색
        dense_res = self.client.search(
            collection_name=col_name,
            query_vector=NamedVector(name="dense", vector=dense_q),
            limit=top_k
        )
        sparse_res = self.client.search(
            collection_name=col_name,
            query_vector=NamedVector(name="sparse", vector=bm25_q),
            limit=top_k
        )
        splade_res = self.client.search(
            collection_name=col_name,
            query_vector=NamedVector(name="splade", vector=splade_q),
            limit=top_k
        )

        # 3) 점수 결합
        ranked = combine_scores(dense_res, sparse_res, splade_res, w_dense=w_dense, w_sparse=w_sparse, w_splade=w_splade)

        # 4) 날짜 가중 (옵션)
        if date_weight > 0.0:
            ranked = self._apply_date_weight(ranked, col_name, start_date, end_date, date_weight)

        # 5) 요약 출력 (텍스트 본문은 출력하지 않고 id/title만)
        if print_summary:
            print_rerank_summary(ranked, self.client, col_name, top_n=summary_top_n)

        return ranked