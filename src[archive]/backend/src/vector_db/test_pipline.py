from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from sparse_helper import bm25_encode, bm25_fit
from splade_module import splade_encode
import os, json
from reranker_module import weighted_fuse, normalize_scores

# 1. BM25 학습용 코퍼스 수집
base_path = "../../../../data/"
all_texts = []

for root, _, files in os.walk(base_path):
    for file in files:
        if file.endswith(".json"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    text = data.get("content") or data.get("contents")
                    if text:
                        all_texts.append(text)
                except json.JSONDecodeError:
                    continue

if not all_texts:
    raise RuntimeError("No text data found for BM25 fitting")

# 2. BM25 모델 학습
bm25_fit(all_texts)
print(f"[BM25] Fitted on {len(all_texts)} documents.")

# 3. Qdrant 및 모델 초기화
client = QdrantClient("http://localhost:6333")
dense_model = SentenceTransformer("jhgan/ko-sroberta-multitask")

query_text = "최신 전산학부 홍보 요청 자료"
dense_query_vec = dense_model.encode(query_text)
# BM25, SPLADE 인코딩
bm25_vec = bm25_encode(query_text)
splade_vec = splade_encode(query_text)

# [OK] dict → SparseVector 변환
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
# 4. 결과 출력 함수
def print_results(results, mode):
    print(f"\n=== {mode.upper()} RESULTS ===")
    for i, r in enumerate(results, 1):
        if isinstance(r, tuple):
            point_id, point = r
        else:
            point_id, point = r.id, r
        title = point.payload.get("title") if hasattr(point, "payload") else None
        print(f"{i:02d}. ID={point_id}, score={point.score:.4f}, title={title}")

# -------------------------------
# 새로 추가: 중복 제거 + 자동 보충용 함수
# -------------------------------
def query_unique_docs(client, collection_name, query, using, top_k=10, step=50, max_limit=1000):
    seen_docs = set()
    unique_results = []
    offset = 0
    limit = step

    while len(unique_results) < top_k and limit <= max_limit:
        results = client.query_points(
            collection_name=collection_name,
            query=query,
            using=using,
            limit=limit,
            offset=offset
        )

        points = results.points if hasattr(results, "points") else results
        if not points:
            break

        for r in points:
            if isinstance(r, tuple):
                point_id, point = r
            else:
                point_id, point = r.id, r

            payload = point.payload
            doc_id = payload.get("doc_id") or payload.get("parent_id") or point_id

            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                unique_results.append(r)

            if len(unique_results) >= top_k:
                break

        offset += step
        limit += step

    return unique_results


# -------------------------------
# [OK] 새로 추가: 평균 점수 기반 문서 단위 dedup
# -------------------------------
def deduplicate_and_average(results, top_k=10):
    doc_scores = {}
    doc_titles = {}

    for r in results:
        if isinstance(r, tuple):
            point_id, point = r
        else:
            point_id, point = r.id, r

        payload = point.payload
        doc_id = payload.get("doc_id") or payload.get("parent_id") or point_id

        doc_scores.setdefault(doc_id, []).append(point.score)
        if doc_id not in doc_titles:
            doc_titles[doc_id] = payload.get("title")

    averaged = [
        {"doc_id": doc_id, "avg_score": sum(scores) / len(scores), "title": doc_titles[doc_id]}
        for doc_id, scores in doc_scores.items()
    ]
    averaged = sorted(averaged, key=lambda x: x["avg_score"], reverse=True)
    return averaged[:top_k]


# -------------------------------
# [OK] 검색 실행 (자동 보충 포함)
# -------------------------------
dense_results = query_unique_docs(client, "notion.marketing", dense_query_vec, "dense", top_k=10)
sparse_results = query_unique_docs(client, "notion.marketing", bm25_vec, "sparse", top_k=10)
splade_results = query_unique_docs(client, "notion.marketing", splade_vec, "splade", top_k=10)

print_results(dense_results, "dense")
print_results(sparse_results, "sparse")
print_results(splade_results, "splade")

# -------------------------------
# [OK] 최종 리랭킹 (문서 단위 평균 점수)
# -------------------------------
print("\n=== FINAL RERANKED RESULTS (AVERAGE-POOLED & DEDUPLICATED) ===")

# 세 검색 결과를 합쳐서 dedup + 평균 점수
all_results = weighted_fuse(dense_results, sparse_results, splade_results)
final_docs = deduplicate_and_average(all_results, top_k=10)

for i, doc in enumerate(final_docs, 1):
    print(f"{i:02d}. DocID={doc['doc_id']}, AvgScore={doc['avg_score']:.4f}, Title={doc['title']}")


# --- 날짜 기반 최신성 점수 보정 ---
from reranker_module import apply_date_window_boost

boosted_docs = apply_date_window_boost(
    final_docs,
    client=client,
    collection_name="notion.marketing",
    date_from="2025-10-01T00:00:00Z",
    date_to="2025-10-03T23:59:59Z",
    decay_rate=0.03,
    weight=0.25
)

print("\n=== DATE-WINDOW BOOSTED RESULTS (2025-10-01 ~ 2025-10-03) ===")
for i, doc in enumerate(boosted_docs, 1):
    print(f"{i:02d}. DocID={doc['doc_id']}, FinalScore={doc['final_score']:.4f}, "
          f"Freshness={doc['freshness']:.3f}, Date={doc.get('date')}, Title={doc['title']}")
# --- Cross-Encoder reranking ---
from reranker_module import load_cross_encoder, rerank_with_cross_encoder, apply_date_window_boost
from datetime import datetime

tokenizer, cross_model = load_cross_encoder()
candidate_texts = []

for doc in final_docs:
    doc_id = doc["doc_id"]
    hits, _ = client.scroll(
        collection_name="notion.marketing",
        scroll_filter=Filter(
            must=[FieldCondition(key="parent_id", match=MatchValue(value=doc_id))]
        ),
        limit=1
    )
    if hits:
        point = hits[0]
        text = point.payload.get("contents") or point.payload.get("content") or ""
        title = point.payload.get("title") or doc.get("title", "(no title)")
        date = point.payload.get("date") or point.payload.get("start")  # [OK] 날짜 필드 가져오기
        candidate_texts.append({
            "id": doc_id,
            "text": text,
            "title": title,
            "date": date
        })

# rerank 수행
reranked_final = rerank_with_cross_encoder(
    query_text, candidate_texts, tokenizer, cross_model, top_k=10
)

print("\n=== CROSS-ENCODER RERANKED RESULTS ===")
for i, doc in enumerate(reranked_final, 1):
    title = doc.get("title", "(no title)")
    print(f"{i:02d}. ID={doc['id']}, Score={doc['score']:.4f}, Title={title}")

# --- [OK] Cross-Encoder 이후 날짜 기반 보정 ---
# 날짜 구간: 2025-10-01 ~ 2025-10-03
boosted_cross = apply_date_window_boost(
    reranked_final,
    client=client,
    collection_name="notion.marketing",
    date_from="2025-10-01T00:00:00Z",
    date_to="2025-10-03T23:59:59Z",
    decay_rate=0.03,
    weight=0.25
)

print("\n=== FINAL CROSS-ENCODER + DATE-BOOSTED RESULTS ===")
for i, doc in enumerate(boosted_cross, 1):
    title = doc.get("title", "(no title)")
    print(f"{i:02d}. ID={doc['id']}, FinalScore={doc['final_score']:.4f}, "
          f"Freshness={doc['freshness']:.3f}, Date={doc.get('date')}, Title={title}")