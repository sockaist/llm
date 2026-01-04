# -*- coding: utf-8 -*-
"""
Fusion Engine for Vector Store.
Handles score fusion (Weighted Sum, RRF), deduplication, and post-processing like Date Boost.
Consolidated from legacy reranker_module.py.
"""

import numpy as np
import math
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Iterable
from qdrant_client.models import Filter, FieldCondition, MatchValue

from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace

# ==========================================================
# Score Normalization & Fusion (Weighted Sum)
# ==========================================================

def normalize_scores(score_dict: Dict[Any, float]) -> Dict[Any, float]:
    """점수 사전을 0~1 범위로 정규화합니다."""
    if not score_dict:
        return {}
    values = np.array(list(score_dict.values()))
    min_v, max_v = values.min(), values.max()
    if max_v - min_v < 1e-8:
        return {k: 0.5 for k in score_dict}
    return {k: (v - min_v) / (max_v - min_v) for k, v in score_dict.items()}


def weighted_fuse(
    dense_results,
    sparse_results,
    splade_results,
    w_dense=0.6,
    w_sparse=0.25,
    w_splade=0.15,
    title_results=None,
    title_weight=0.0,
) -> List[Tuple[Any, Dict[str, Any]]]:
    """Dense, Sparse(BM25), SPLADE 점수를 가중합으로 통합합니다."""
    trace("Combining scores via Weighted Fusion")

    dense_dict = {r.id: r.score for r in dense_results}
    sparse_dict = {r.id: r.score for r in sparse_results}
    splade_dict = {r.id: r.score for r in splade_results}
    title_dict = {r.id: r.score for r in (title_results or [])}

    dn = normalize_scores(dense_dict)
    sn = normalize_scores(sparse_dict)
    spn = normalize_scores(splade_dict)
    tn = normalize_scores(title_dict)

    all_ids = set(dn.keys()) | set(sn.keys()) | set(spn.keys()) | set(tn.keys())
    
    # Store payloads for fast access
    id_to_payload = {}
    for r in (list(dense_results) + list(sparse_results) + 
              list(splade_results) + list(title_results or [])):
        if r.id not in id_to_payload and getattr(r, "payload", None):
            id_to_payload[r.id] = r.payload

    combined = {}
    for pid in all_ids:
        d = dn.get(pid, 0.0)
        s = sn.get(pid, 0.0)
        sp = spn.get(pid, 0.0)
        t = tn.get(pid, 0.0)

        final = w_dense * d + w_sparse * s + w_splade * sp + title_weight * t
        combined[pid] = {
            "dense": d, "sparse": s, "splade": sp, "title": t,
            "final": final, "score": final, "payload": id_to_payload.get(pid, {})
        }

    ranked = sorted(combined.items(), key=lambda x: x[1]["final"], reverse=True)
    return ranked


# ==========================================================
# Reciprocal Rank Fusion (RRF)
# ==========================================================

def reciprocal_rank_fusion(
    dense_results,
    sparse_results,
    splade_results,
    k=60,
    title_results=None,
    weights=None,
) -> List[Tuple[Any, Dict[str, Any]]]:
    """RRF 알고리즘을 사용하여 여러 검색 결과를 통합합니다."""
    trace(f"Running RRF Fusion (k={k})")

    methods = {
        "dense": dense_results,
        "sparse": sparse_results,
        "splade": splade_results,
        "title": title_results or [],
    }

    w_map = weights or {"dense": 1.0, "sparse": 1.0, "splade": 1.0, "title": 1.0}
    doc_scores = {}
    doc_payloads = {}

    for method, results in methods.items():
        weight = w_map.get(method, 1.0)
        if not results: continue

        for rank, r in enumerate(results):
            pid = getattr(r, "id", None)
            if not pid: continue

            if pid not in doc_payloads and getattr(r, "payload", None):
                doc_payloads[pid] = r.payload

            score = weight * (1.0 / (k + rank + 1))
            if pid not in doc_scores:
                doc_scores[pid] = {"dense": 0, "sparse": 0, "splade": 0, "title": 0, "final": 0}
            
            doc_scores[pid][method] = score
            doc_scores[pid]["final"] += score

    ranked_list = []
    for pid, scores in doc_scores.items():
        payload = doc_payloads.get(pid, {})
        ranked_list.append((pid, {**scores, "payload": payload, "score": scores["final"]}))

    ranked_list.sort(key=lambda x: x[1]["final"], reverse=True)
    return ranked_list


# ==========================================================
# Deduplication (청크 단위 중복 제거)
# ==========================================================

def deduplicate_results(
    results, client=None, col_name: str = None, top_k=10
) -> List[Dict[str, Any]]:
    """동일 문서(db_id)의 여러 청크를 대표 점수(평균)로 통합합니다."""
    trace(f"Deduplicating results for {col_name or 'unknown collection'}")
    doc_scores, doc_payloads = {}, {}

    for r in results:
        # Tuple (id, dict) or Object
        if isinstance(r, tuple):
            pid, data = r
            payload = data.get("payload", {})
            score = data.get("final", data.get("score", 0.0))
        else:
            pid = getattr(r, "id", None)
            payload = getattr(r, "payload", {}) or {}
            score = getattr(r, "score", 0.0)

        raw_id = payload.get("db_id") or payload.get("parent_id") or payload.get("id") or pid
        if raw_id is None: continue
        uid = str(raw_id)

        doc_scores.setdefault(uid, []).append(score)
        if uid not in doc_payloads:
            doc_payloads[uid] = payload

    averaged = []
    for uid, scores in doc_scores.items():
        payload = doc_payloads[uid]
        averaged.append({
            "db_id": uid,
            "avg_score": sum(scores) / len(scores),
            "title": payload.get("title"),
            "text": payload.get("text") or payload.get("content") or "",
            "payload": payload,
        })

    averaged.sort(key=lambda x: x["avg_score"], reverse=True)
    return averaged[:top_k]


# ==========================================================
# Temporal Ranking & Intent Detection (Consolidated)
# ==========================================================

def extract_temporal_intent(query: str) -> Dict[str, Any]:
    """쿼리에서 시간적 의도(최신성 요구) 및 명시적 연도를 추출합니다."""
    query_lower = query.lower()
    recent_keywords = ["최신", "최근", "오늘", "뉴스", "올해", "recent", "latest"]
    
    year_match = re.search(r"(20[12]\d)", query)
    explicit_year = int(year_match.group(1)) if year_match else None
    has_recent = any(kw in query_lower for kw in recent_keywords) or (explicit_year is not None)
    
    return {
        "has_recent_intent": has_recent,
        "explicit_year": explicit_year,
        "alpha": 0.5 if has_recent else 0.8,
        "half_life": 365.0 if explicit_year or has_recent else 730.0
    }


def apply_temporal_ranking(
    results: List[Dict[str, Any]],
    alpha: float = 0.7,
    half_life_days: float = 14.0,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """의미론적 점수와 시간적 최신성 점수를 결합하여 재정렬합니다."""
    if not results: return []
    trace(f"Applying Temporal Ranking (alpha={alpha}, half_life={half_life_days})")
    
    now = datetime.now(timezone.utc)
    scores = [r.get("avg_score", r.get("score", 0.0)) for r in results]
    s_min, s_max = min(scores), max(scores)

    for r in results:
        raw_score = r.get("avg_score", r.get("score", 0.0))
        norm_score = (raw_score - s_min) / (s_max - s_min) if s_max != s_min else 0.5

        payload = r.get("payload", {})
        date_val = payload.get("date") or payload.get("publish_date")
        
        doc_date = None
        if isinstance(date_val, str):
            try: doc_date = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
            except: pass
        elif isinstance(date_val, datetime):
            doc_date = date_val

        if doc_date:
            if not doc_date.tzinfo: doc_date = doc_date.replace(tzinfo=timezone.utc)
            age_days = max(0, (now - doc_date).total_seconds() / (24 * 3600))
            recency_score = math.exp(-math.log(2) * age_days / half_life_days)
        else:
            recency_score = 0.3 # Neutral fallback

        final_score = alpha * norm_score + (1 - alpha) * recency_score
        r.update({
            "cosine_similarity": norm_score,
            "recency_score": recency_score,
            "original_score": raw_score,
            "score": final_score,
            "final_score": final_score
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def _parse_date(payload: Dict[str, Any]) -> Optional[datetime]:
    """Payload에서 날짜 정보를 추출합니다."""
    date_fields = ["date", "created_at", "updated_at"]
    for f in date_fields:
        val = payload.get(f)
        if isinstance(val, datetime): return val
        if isinstance(val, str):
            try:
                # Simple extraction
                match = re.search(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", val)
                if match:
                    return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), tzinfo=timezone.utc)
            except: continue
    return None


# ==========================================================
# Payload Fetching (Reranking 준비)
# ==========================================================

def fetch_payloads(client, merged, top_k=5) -> List[Dict[str, Any]]:
    """중복 제거된 결과를 바탕으로 Reranking에 필요한 전체 Payload를 가져옵니다."""
    trace(f"Fetching payloads for top {top_k} results")
    enriched = []
    for d in merged[:top_k]:
        try:
            db_id = d.get("db_id")
            col = d.get("collection")
            if not db_id or not col: continue

            # Direct retrieve
            hits = client.retrieve(collection_name=col, ids=[db_id], with_payload=True)
            if not hits:
                # Fallback to parent_id scroll
                hits, _ = client.scroll(
                    collection_name=col,
                    scroll_filter=Filter(must=[FieldCondition(key="parent_id", match=MatchValue(value=db_id))]),
                    limit=1
                )
            
            if hits:
                payload = hits[0].payload or {}
                enriched.append({
                    "id": db_id,
                    "collection": col,
                    "title": payload.get("title", d.get("title")),
                    "text": payload.get("content") or payload.get("text") or "",
                })
        except Exception as e:
            logger.warning(f"Failed to fetch payload for {d.get('db_id')}: {e}")
    
    return enriched
