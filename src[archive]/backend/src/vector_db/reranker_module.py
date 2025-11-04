# reranker_module.py
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

def normalize_scores(score_dict):
    """
    각 점수 사전을 0~1 범위로 정규화
    """
    if not score_dict:
        return {}
    values = np.array(list(score_dict.values()))
    min_v, max_v = values.min(), values.max()
    if max_v - min_v < 1e-8:
        return {k: 0.5 for k in score_dict}  # 모든 점수가 동일하면 0.5로 고정
    return {k: (v - min_v) / (max_v - min_v) for k, v in score_dict.items()}


def combine_scores(
    dense_results,
    sparse_results,
    splade_results,
    w_dense=0.6,
    w_sparse=0.25,
    w_splade=0.15,
):
    """
    Dense, Sparse(BM25), SPLADE 점수를 가중합으로 통합하고,
    각 점수별 상세를 함께 반환
    """
    dense_dict = {r.id: r.score for r in dense_results}
    sparse_dict = {r.id: r.score for r in sparse_results}
    splade_dict = {r.id: r.score for r in splade_results}

    dense_norm = normalize_scores(dense_dict)
    sparse_norm = normalize_scores(sparse_dict)
    splade_norm = normalize_scores(splade_dict)

    all_ids = set(dense_norm.keys()) | set(sparse_norm.keys()) | set(splade_norm.keys())

    combined = {}
    for pid in all_ids:
        d = dense_norm.get(pid, 0)
        s = sparse_norm.get(pid, 0)
        sp = splade_norm.get(pid, 0)
        combined[pid] = {
            "dense": d,
            "sparse": s,
            "splade": sp,
            "final": w_dense * d + w_sparse * s + w_splade * sp
        }

    ranked = sorted(combined.items(), key=lambda x: x[1]["final"], reverse=True)
    return ranked


def print_rerank_summary(ranked, client, col_name, top_n=10):
    """
    rerank 결과 요약 출력 (dense/sparse/splade 개별 점수 포함)
    """
    print("\n=== RERANKED RESULTS (Detailed) ===")
    for idx, (pid, scores) in enumerate(ranked[:top_n]):
        doc = client.retrieve(collection_name=col_name, ids=[pid], with_payload=True)
        if not doc:
            continue
        payload = doc[0].payload
        title = payload.get("title", "(no title)")
        parent_id = payload.get("parent_id", "?")
        print(f"{idx+1:02d}. Chunk ID={pid}, Doc ID={parent_id}")
        print(f"    Title: {title}")
        print(f"    dense={scores['dense']:.3f}, sparse={scores['sparse']:.3f}, splade={scores['splade']:.3f} → final={scores['final']:.3f}")
    print("===================================\n")
    
    
def deduplicate_by_doc(reranked_results, client, col_name, top_k=10):
    """
    동일 문서(doc_id)가 여러 번 등장하면 한 번만 남기고,
    부족한 개수는 그 아래 순위 문서로 채움.
    """
    unique_docs = {}
    final_results = []

    for r in reranked_results:
        payload = client.retrieve(collection_name=col_name, ids=[r.id])[0].payload
        doc_id = payload.get("parent_id", payload.get("doc_id", r.id))

        # 아직 이 문서(doc_id)가 추가되지 않았으면 추가
        if doc_id not in unique_docs:
            unique_docs[doc_id] = r
            final_results.append((doc_id, r))

        # 이미 포함된 문서라면 스킵
        if len(final_results) >= top_k:
            break

    # 부족하면 뒤에서 보충
    if len(final_results) < top_k:
        for r in reranked_results[len(final_results):]:
            payload = client.retrieve(collection_name=col_name, ids=[r.id])[0].payload
            doc_id = payload.get("parent_id", payload.get("doc_id", r.id))
            if doc_id not in unique_docs:
                unique_docs[doc_id] = r
                final_results.append((doc_id, r))
            if len(final_results) >= top_k:
                break

    return final_results


def deduplicate_and_average(results, client, col_name, top_k=10):
    """
    동일 문서(doc_id)의 여러 chunk가 있을 경우 평균 점수를 계산하여 하나만 남김
    """
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

# --- (1) 정규화 함수 ---
def normalize_scores(results, mode):
    """
    검색 결과 점수를 0~1 범위로 정규화 (모델별 방식)
    - SPLADE: softmax
    - Dense/BM25: min-max scaling
    """
    scores = np.array([r.score for r in results])
    if len(scores) == 0:
        return results

    if mode == "splade":
        exp_scores = np.exp(scores - np.max(scores))
        norm_scores = exp_scores / np.sum(exp_scores)
    else:
        min_s, max_s = np.min(scores), np.max(scores)
        if max_s == min_s:
            norm_scores = np.ones_like(scores)
        else:
            norm_scores = (scores - min_s) / (max_s - min_s)

    for r, s in zip(results, norm_scores):
        if isinstance(r, tuple):
            r[1].score = float(s)
        else:
            r.score = float(s)
    return results


# --- (2) 가중치 기반 점수 결합 ---
def weighted_fuse(dense_results, sparse_results, splade_results,
                  w_dense=0.6, w_sparse=0.3, w_splade=0.1):
    """
    세 검색 결과의 점수를 정규화 후 가중합으로 결합
    """
    dense_results = normalize_scores(dense_results, "dense")
    sparse_results = normalize_scores(sparse_results, "sparse")
    splade_results = normalize_scores(splade_results, "splade")

    for result_set, w in zip(
        [dense_results, sparse_results, splade_results],
        [w_dense, w_sparse, w_splade],
    ):
        for r in result_set:
            if isinstance(r, tuple):
                r[1].score *= w
            else:
                r.score *= w

    return dense_results + sparse_results + splade_results

# --- Cross-Encoder Reranker 초기화 ---
def load_cross_encoder(model_name="Dongjin-kr/ko-reranker"):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    return tokenizer, model


# --- Cross-Encoder 기반 reranking ---
def rerank_with_cross_encoder(query, docs, tokenizer, model, top_k=10, device="cpu"):
    pairs = [(query, d["text"]) for d in docs]
    inputs = tokenizer(
        [q for q, d in pairs],
        [d for q, d in pairs],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        scores = model(**inputs).logits.squeeze(-1).cpu().numpy()

    reranked = [
        {"id": d["id"], "text": d["text"], "title": d.get("title"), "score": float(scores[i])}
        for i, d in enumerate(docs)
    ]
    reranked.sort(key=lambda x: x["score"], reverse=True)
    return reranked[:top_k]

import math
import re
from datetime import datetime, timezone

def extract_date_from_text(text: str):
    """
    문자열에서 날짜(YYYY-MM-DD, YYYY년 MM월 DD일 등)를 추출하는 함수
    """
    if not text:
        return None

    patterns = [
        r"(\d{4})[-./년\s]*(\d{1,2})[-./월\s]*(\d{1,2})",  # 2025-10-29 / 2025년 10월 29일 등
        r"(\d{4})[-./](\d{1,2})"  # 2025-10
    ]

    for p in patterns:
        match = re.search(p, text)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 3:
                    year, month, day = groups
                elif len(groups) == 2:
                    year, month = groups
                    day = 1  # 일(day)이 없으면 기본값 1로
                else:
                    continue

                # timezone-aware datetime으로 반환 (UTC)
                return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
            except Exception:
                continue

    return None


from datetime import datetime, timezone

def parse_date_field(payload):
    """
    payload(dict)에서 가능한 모든 날짜 필드를 확인하고 가장 최근 날짜를 반환
    - date, finish, start, meta.date 등 다층 탐색
    """
    fields = []
    if not isinstance(payload, dict):
        return None

    # 1단계: 루트 레벨 key 확인
    for key in ["date", "finish", "start"]:
        if key in payload:
            fields.append(payload[key])

    # 2단계: meta 내부 탐색
    meta = payload.get("meta") or {}
    if isinstance(meta, dict):
        for key in ["date", "finish", "start"]:
            if key in meta:
                fields.append(meta[key])

    # 3단계: contents/title 내부 문자열 탐색
    for key in ["contents", "content", "title"]:
        txt = payload.get(key)
        if txt and isinstance(txt, str):
            extracted = extract_date_from_text(txt)
            if extracted:
                fields.append(extracted)

    # 4단계: 가능한 날짜 문자열을 datetime으로 변환
    parsed_dates = []
    for f in fields:
        if isinstance(f, datetime):
            parsed_dates.append(f)
        elif isinstance(f, str):
            f_clean = f.strip().replace(" ", "").replace("년", "-").replace("월", "-").replace("일", "")
            try:
                if "T" in f_clean:
                    dt = datetime.fromisoformat(f_clean.replace("Z", "+00:00"))
                else:
                    dt = extract_date_from_text(f_clean)
                if dt:
                    parsed_dates.append(dt)
            except Exception:
                continue

    if not parsed_dates:
        return None

    # 여기서 모든 datetime을 UTC로 통일
    normalized = []
    for d in parsed_dates:
        if d.tzinfo is None:
            normalized.append(d.replace(tzinfo=timezone.utc))
        else:
            normalized.append(d.astimezone(timezone.utc))

    return max(normalized)


def apply_date_window_boost(results, client=None, collection_name=None,
                            date_from=None, date_to=None, decay_rate=0.02, weight=0.45):
    """
    Cross-Encoder나 Average Reranker 결과 리스트에 대해
    '최근 3개월' 기준으로 최신성 boost를 주는 극적 가중 버전
    """
    now = datetime.utcnow()

    # 1️⃣ Cross-Encoder 점수 정규화
    scores = np.array([r.get("score", 0.0) for r in results])
    if len(scores) > 0:
        min_s, max_s = scores.min(), scores.max()
        for r in results:
            if max_s != min_s:
                r["score_norm"] = (r.get("score", 0.0) - min_s) / (max_s - min_s)
            else:
                r["score_norm"] = 0.5
    else:
        for r in results:
            r["score_norm"] = 0.5

    def parse_input_date(d):
        if d is None:
            return None
        if isinstance(d, str):
            return datetime.fromisoformat(d.replace("Z", "+00:00"))
        return d

    date_from = parse_input_date(date_from)
    date_to = parse_input_date(date_to)

    boosted = []
    for r in results:
        doc_id = (
            r.get("id")
            or r.get("doc_id")
            or r.get("parent_id")
            or getattr(r, "id", None)
        )

        base_score = r.get("avg_score", r.get("score_norm", 0.0))

        # Qdrant에서 payload 읽기
        if client and collection_name and doc_id is not None:
            try:
                fetched = client.retrieve(collection_name=collection_name, ids=[doc_id], with_payload=True)
                payload = fetched[0].payload if fetched else {}
            except Exception:
                payload = {}
        else:
            payload = r if isinstance(r, dict) else getattr(r, "payload", {})

        doc_date = parse_date_field(payload)
        if not doc_date:
            text = payload.get("contents") or payload.get("content") or payload.get("title", "")
            doc_date = extract_date_from_text(text)

        # 2️최신성 계산 (3개월 기준 감쇠)
        if not doc_date:
            freshness = 0.5
        else:
            # aware/naive 혼용 방지: UTC 기준으로 통일
            if doc_date.tzinfo is not None and doc_date.tzinfo.utcoffset(doc_date) is not None:
                doc_date = doc_date.replace(tzinfo=None)

            delta_days = abs((now - doc_date).days)
            freshness = math.exp(-decay_rate * delta_days)  # 0~1 사이

        # 3️비선형 가중 결합 (극적 효과)
        boosted_score = base_score * math.exp(weight * (freshness - 0.5))

        boosted.append({
            **r,
            "freshness": round(freshness, 4),
            "final_score": boosted_score,
            "date": doc_date.isoformat() if doc_date else None
        })

    boosted = sorted(boosted, key=lambda x: x["final_score"], reverse=True)
    return boosted