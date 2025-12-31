"""Temporal Ranking and Date Filtering for RAG."""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from llm_backend.utils.logger import logger

def parse_iso_date(date_str: str) -> Optional[datetime]:
    """Parse ISO 8601 date string with support for 'Z' and offsets."""
    if not date_str:
        return None
    try:
        # Handle 'Z' as +00:00
        clean_str = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None

def calculate_recency_score(doc_date: datetime, half_life_days: float = 14.0) -> float:
    """
    Calculate recency score using exponential decay: exp(-ln(2) * age / half_life).
    Score is 1.0 for now, 0.5 for half-life age.
    """
    now = datetime.now(timezone.utc)
    if not doc_date.tzinfo:
        doc_date = doc_date.replace(tzinfo=timezone.utc)
        
    age_delta = now - doc_date
    age_days = max(0, age_delta.total_seconds() / (24 * 3600))
    
    # Formula: score = exp(-ln(2) * age / half_life)
    return math.exp(-math.log(2) * age_days / half_life_days)

def apply_temporal_ranking(
    results: List[Dict[str, Any]],
    alpha: float = 0.7,
    half_life_days: float = 14.0,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Apply recency-based re-ranking to a list of results.
    Final Score = alpha * semantic_score + (1 - alpha) * recency_score
    """
    if not results:
        return []

    # 1. Normalize scores to 0-1 range first if they aren't already
    scores = [r.get("avg_score", r.get("score", 0.0)) for r in results]
    min_s, max_s = min(scores), max(scores)
    
    for r in results:
        raw_score = r.get("avg_score", r.get("score", 0.0))
        norm_score = (raw_score - min_s) / (max_s - min_s) if max_s != min_s else 0.5
        
        # 2. Extract date from payload
        payload = r.get("payload", {})
        date_val = payload.get("date") or payload.get("publish_date")
        
        rec_score = 0.0
        doc_date = None
        if date_val:
            doc_date = parse_iso_date(date_val) if isinstance(date_val, str) else date_val
            
        if doc_date:
            rec_score = calculate_recency_score(doc_date, half_life_days)
        else:
            # If no date, use a neutral base recency score (e.g., 0.3)
            rec_score = 0.3
            
        final_score = alpha * norm_score + (1 - alpha) * rec_score
        
        r["cosine_similarity"] = norm_score
        r["recency_score"] = rec_score
        r["original_score"] = raw_score
        r["score"] = final_score # Overwrite the score for sorting
        if doc_date:
            r["publish_date"] = doc_date.isoformat()

    # Sort by the new combined score
    results.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"[Temporal] Reranked {len(results)} docs with alpha={alpha}, half_life={half_life_days}")
    
    return results[:top_k]

def extract_temporal_intent(query: str) -> Dict[str, Any]:
    """
    Enhanced heuristic for temporal intent.
    Identifies 'recent' intent and explicit years.
    """
    query_lower = query.lower()
    recent_keywords = ["최신", "최근", "오늘", "뉴스", "올해", "last week", "recent", "latest"]
    
    # Check for explicit years (Handle cases like '2021년')
    import re
    year_match = re.search(r"(20[12]\d)", query)
    explicit_year = int(year_match.group(1)) if year_match else None

    has_recent_intent = any(kw in query_lower for kw in recent_keywords) or (explicit_year is not None)
    
    # Domain-aware defaults: for research data, half-life should be longer
    return {
        "has_recent_intent": has_recent_intent,
        "explicit_year": explicit_year,
        "alpha": 0.5 if has_recent_intent else 0.8,
        "half_life": 365.0 if explicit_year or has_recent_intent else 730.0 # 1-2 years
    }
