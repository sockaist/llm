import numpy as np
import math
import re
import torch
from datetime import datetime, timezone
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from qdrant_client.models import Filter, FieldCondition, MatchValue

# --------------------------------------------
# 기본 점수 정규화 및 결합
# --------------------------------------------

def normalize_scores(score_dict):
    """각 점수 사전을 0~1 범위로 정규화"""
    if not score_dict:
        return {}
    values = np.array(list(score_dict.values()))
    min_v, max_v = values.min(), values.max()
    if max_v - min_v < 1e-8:
        return {k: 0.5 for k in score_dict}
    return {k: (v - min_v) / (max_v - min_v) for k, v in score_dict.items()}


def combine_scores(dense_results, sparse_results, splade_results,
                   w_dense=0.6, w_sparse=0.25, w_splade=0.15,
                   title_results=None, title_weight=0.0):
    """Dense, Sparse(BM25), SPLADE, and Title 점수를 가중합으로 통합"""
    trace("Combining scores across multi-vector results")

    dense_dict = {r.id: r.score for r in dense_results}
    sparse_dict = {r.id: r.score for r in sparse_results}
    splade_dict = {r.id: r.score for r in splade_results}
    title_dict = {r.id: r.score for r in (title_results or [])}

    dense_norm = normalize_scores(dense_dict)
    sparse_norm = normalize_scores(sparse_dict)
    splade_norm = normalize_scores(splade_dict)
    title_norm = normalize_scores(title_dict)

    all_ids = set(dense_norm.keys()) | set(sparse_norm.keys()) | set(splade_norm.keys()) | set(title_norm.keys())
    
    # Create a map for easy payload access
    id_to_payload = {}
    for r in list(dense_results) + list(sparse_results) + list(splade_results) + list(title_results or []):
        if r.id not in id_to_payload and getattr(r, "payload", None):
            id_to_payload[r.id] = r.payload

    combined = {}

    for pid in all_ids:
        d = dense_norm.get(pid, 0)
        s = sparse_norm.get(pid, 0)
        sp = splade_norm.get(pid, 0)
        t = title_norm.get(pid, 0)
        
        # Calculate final weighted score
        final_score = w_dense * d + w_sparse * s + w_splade * sp + title_weight * t
        
        combined[pid] = {
            "dense": d,
            "sparse": s,
            "splade": sp,
            "title": t,
            "final": final_score,
            "score": final_score,
            "payload": id_to_payload.get(pid, {}),
        }

    ranked = sorted(combined.items(), key=lambda x: x[1]["final"], reverse=True)
    logger.debug(f"Combined {len(ranked)} documents (Phase 5: Multi-Vector) after score fusion")
    return ranked

weighted_fuse = combine_scores

def reciprocal_rank_fusion(dense_results, sparse_results, splade_results, k=60, 
                         title_results=None, weights=None):
    """
    RRF (Reciprocal Rank Fusion) algorithm.
    Score = sum(1 / (k + rank_i)) for each method.
    Using simple summation by default. weights dict can be used to bias specific methods if needed.
    """
    trace(f"Running RRF Fusion (k={k})")
    
    # Define method mapping
    methods = {
        "dense": dense_results,
        "sparse": sparse_results,
        "splade": splade_results,
        "title": title_results or []
    }
    
    # Weights for weighted RRF (Optional, default 1.0)
    # If weights provided, multiply final score component by weight? 
    # Standard RRF doesn't use weights, but we can do Weighted RRF: w * (1/(k+r))
    w_map = weights or {"dense": 1.0, "sparse": 1.0, "splade": 1.0, "title": 1.0}
    
    doc_scores = {}
    doc_payloads = {}
    
    for method_name, results in methods.items():
        weight = w_map.get(method_name, 1.0)
        if not results:
            continue
        
        # Sort just in case (though usually they come sorted)
        # We trust inputs are sorted by their native score
        
        for rank, r in enumerate(results):
            # Create unique key
            pid = getattr(r, "id", None)
            if not pid:
                continue
            
            # Cache payload if available
            if pid not in doc_payloads and getattr(r, 'payload', None):
                doc_payloads[pid] = r.payload
                
            # RRF Formula
            score = weight * (1.0 / (k + rank + 1))
            
            if pid not in doc_scores:
                doc_scores[pid] = {
                    "dense": 0.0, "sparse": 0.0, "splade": 0.0, "title": 0.0, "final": 0.0
                }
            
            doc_scores[pid][method_name] = score # Store component score (this is RRF contribution)
            doc_scores[pid]["final"] += score

    # Format result compatible with existing pipeline
    ranked_list = []
    for pid, scores in doc_scores.items():
        payload = doc_payloads.get(pid, {})
        ranked_list.append({
            "id": pid,
            "score": scores["final"],
            "final": scores["final"],
            "payload": payload,
            "dense": scores["dense"],
            "sparse": scores["sparse"],
            "splade": scores["splade"],
            "title": scores["title"]
        })
        
    ranked_list.sort(key=lambda x: x["final"], reverse=True)
    logger.debug(f"RRF Fused {len(ranked_list)} docs")
    
    # Transform to list of tuple (id, dict) to match combine_scores signature essentially?
    # No, combine_scores returns list of tuples: (pid, dict_of_scores)
    # The pipeline expects this format at line 209: `for d in doclevel: ... d['id'] = d.get('db_id')`
    # Wait, combine_scores returns `ranked = sorted(combined.items(), ...)` which is `[(pid, val_dict), ...]`
    
    return [(d['id'], d) for d in ranked_list]



# --------------------------------------------
# Deduplication (문서 단위 중복 제거)
# --------------------------------------------

def deduplicate_and_average(results, client, col_name, top_k=10):
    """
    동일 문서(db_id)의 여러 chunk 점수를 평균내어 하나만 남김.
    기존 doc_id 대신 JSON 기반 db_id(SHA-256)를 기준으로 그룹화.
    """
    trace(f"Deduplicating results for collection: {col_name}")
    doc_scores, doc_titles, doc_texts, doc_payloads = {}, {}, {}, {}

    for r in results:
        # ScoredPoint 또는 dict 모두 허용
        if isinstance(r, tuple):
            point_id, point = r
        else:
            point_id, point = getattr(r, "id", None), r

        # payload 추출
        if hasattr(point, "payload"):
            payload = point.payload or {}
            score = getattr(point, "score", 0.0)
        elif isinstance(point, dict):
            payload = point.get("payload", {}) or {}
            score = point.get("score", 0.0)
        else:
            payload, score = {}, 0.0

        # 통일된 db_id 기준으로 그룹핑
        db_id = (
            payload.get("db_id")
            or payload.get("id")
            or point_id
        )
        if db_id is None:
            continue

        doc_scores.setdefault(db_id, []).append(score)
        if db_id not in doc_payloads:
            doc_payloads[db_id] = payload
        if db_id not in doc_titles:
            doc_titles[db_id] = payload.get("title")
        if db_id not in doc_texts:
            doc_texts[db_id] = (
                payload.get("text")
                or payload.get("content")
                or payload.get("contents")
                or ""
            )

    # 평균 점수 계산
    averaged = [
        {
            "db_id": db_id,
            "avg_score": sum(scores) / len(scores),
            "title": doc_titles.get(db_id),
            "text": doc_texts.get(db_id, ""),
            "payload": doc_payloads.get(db_id, {})
        }
        for db_id, scores in doc_scores.items()
    ]

    # 점수 내림차순 정렬
    averaged = sorted(averaged, key=lambda x: x["avg_score"], reverse=True)
    logger.debug(f"Deduplicated to {len(averaged)} unique docs (using db_id)")
    return averaged[:top_k]


# --------------------------------------------
# Reranker 로드 및 Cross-Encoder 기반 재정렬
# --------------------------------------------

def load_cross_encoder(model_name="Dongjin-kr/ko-reranker"):
    """Cross-Encoder 모델과 토크나이저 로드"""
    trace(f"Loading Cross-Encoder model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    logger.info(f"Cross-Encoder '{model_name}' loaded successfully")
    return tokenizer, model


def rerank_with_cross_encoder(query, docs, tokenizer, model, top_k=10, device="cpu"):
    """Cross-Encoder 기반 reranking 수행"""
    trace(f"Reranking {len(docs)} documents for query: '{query}'")
    pairs = [(query, d["text"]) for d in docs]
    inputs = tokenizer(
        [q for q, _ in pairs],
        [d for _, d in pairs],
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
    logger.info(f"Reranking completed (top {top_k} returned)")
    return reranked[:top_k]


# --------------------------------------------
# 날짜 기반 부스팅
# --------------------------------------------

def extract_date_from_text(text: str):
    """문자열에서 날짜(YYYY-MM-DD, YYYY년 MM월 DD일 등)를 추출"""
    if not text:
        return None

    patterns = [
        r"(\d{4})[-./년\s]*(\d{1,2})[-./월\s]*(\d{1,2})",
        r"(\d{4})[-./](\d{1,2})"
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
                    day = 1
                else:
                    continue
                return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def parse_date_field(payload):
    """payload(dict)에서 가능한 날짜 필드를 확인하고 가장 최근 날짜를 반환"""
    if not isinstance(payload, dict):
        return None

    fields = []
    for key in ["date", "finish", "start"]:
        if key in payload:
            fields.append(payload[key])

    meta = payload.get("meta") or {}
    if isinstance(meta, dict):
        for key in ["date", "finish", "start"]:
            if key in meta:
                fields.append(meta[key])

    for key in ["contents", "content", "title"]:
        txt = payload.get(key)
        if txt and isinstance(txt, str):
            extracted = extract_date_from_text(txt)
            if extracted:
                fields.append(extracted)

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

    normalized = [d if d.tzinfo else d.replace(tzinfo=timezone.utc) for d in parsed_dates]
    return max(normalized)


def apply_date_window_boost(results, client=None, collection_name=None,
                            date_from=None, date_to=None, decay_rate=0.02, weight=0.45):
    """검색 결과에 날짜 기반 가중치 부여 (최근일수록 점수 boost)"""
    trace(f"Applying date boost (decay={decay_rate}, weight={weight})")
    now = datetime.utcnow()

    # Cross-Encoder 점수 정규화
    scores = np.array([r.get("score", 0.0) for r in results])
    if len(scores) > 0:
        min_s, max_s = scores.min(), scores.max()
        for r in results:
            r["score_norm"] = (r.get("score", 0.0) - min_s) / (max_s - min_s) if max_s != min_s else 0.5
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
        doc_id = r.get("id") or r.get("doc_id") or r.get("parent_id") or getattr(r, "id", None)
        base_score = r.get("avg_score", r.get("score_norm", 0.0))

        # Qdrant에서 payload 읽기
        if client and collection_name and doc_id is not None:
            try:
                fetched = client.retrieve(collection_name=collection_name, ids=[doc_id], with_payload=True)
                payload = fetched[0].payload if fetched else {}
            except Exception as e:
                logger.debug(f"Failed to retrieve doc {doc_id}: {e}")
                payload = {}
        else:
            payload = r if isinstance(r, dict) else getattr(r, "payload", {})

        doc_date = parse_date_field(payload)
        if not doc_date:
            text = payload.get("contents") or payload.get("content") or payload.get("title", "")
            doc_date = extract_date_from_text(text)

        # 최신성 계산
        if not doc_date:
            freshness = 0.5
        else:
            if doc_date.tzinfo is not None and doc_date.tzinfo.utcoffset(doc_date) is not None:
                doc_date = doc_date.replace(tzinfo=None)
            delta_days = abs((now - doc_date).days)
            freshness = math.exp(-decay_rate * delta_days)

        boosted_score = base_score * math.exp(weight * (freshness - 0.5))
        boosted.append({
            **r,
            "freshness": round(freshness, 4),
            "final_score": boosted_score,
            "date": doc_date.isoformat() if doc_date else None
        })

    boosted = sorted(boosted, key=lambda x: x["final_score"], reverse=True)
    logger.info(f"Date boost applied to {len(boosted)} results")
    return boosted

def fetch_payloads_for_rerank(client, merged, top_k=5):
    """
    deduplicate_and_average로 얻은 merged 문서 리스트를 기반으로
    Qdrant에서 실제 payload(text, title 등)를 다시 가져옵니다.
    이제 doc_id 해시 대신 JSON 기반 db_id(SHA-256)를 사용합니다.
    """
    trace(f"Fetching payloads for {len(merged)} merged docs (top_k={top_k})")
    enriched_docs = []

    for d in merged[:top_k]:
        try:
            # 우선 db_id 가져오기
            db_id = d.get("db_id") or d.get("id") or d.get("parent_id")
            col = d.get("collection")
            if not db_id or not col:
                logger.debug(f"[CrossEncoder] Skip: missing db_id or collection in {d}")
                continue

            # Qdrant에서 직접 db_id 기반 조회
            hits = []
            try:
                hits = client.retrieve(
                    collection_name=col,
                    ids=[db_id],
                    with_payload=True
                )
            except Exception as e:
                logger.debug(f"[CrossEncoder] direct retrieve failed for db_id={db_id}: {e}")

            # fallback: parent_id 혹은 id 기반 scroll 검색
            if not hits:
                try:
                    hits, _ = client.scroll(
                        collection_name=col,
                        scroll_filter=Filter(must=[
                            FieldCondition(key="parent_id", match=MatchValue(value=db_id))
                        ]),
                        limit=1,
                        with_payload=True
                    )
                except Exception:
                    hits = []
            
            if not hits:
                logger.debug(f"[CrossEncoder] No hits found for db_id={db_id}")
                continue

            hit = hits[0]
            payload = hit.payload or {}

            enriched_docs.append({
                "id": db_id,  # 이제 db_id로 통일
                "collection": col,
                "title": payload.get("title") or d.get("title") or "(no title)",
                "text": payload.get("content") or payload.get("contents") or payload.get("text", "")
            })

        except Exception as e:
            logger.warning(f"[CrossEncoder] Failed to fetch payload for {d.get('db_id') or d.get('id')}: {e}")

    logger.debug(f"[CrossEncoder] Retrieved {len(enriched_docs)} payloads for reranking")
    return enriched_docs