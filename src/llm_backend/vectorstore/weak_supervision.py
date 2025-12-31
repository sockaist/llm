from typing import Dict, Any, List, Optional
import re
from .dynamic_db import dynamic_db
from llm_backend.utils.logger import logger

class WeakSupervisionEngine:
    """
    Phase 8: Weak Supervision Engine.
    Combines multiple fuzzy signals (Labeling Functions) to predict metadata/entities.
    """

    @classmethod
    def lf_exact_match(cls, query: str, field: str) -> List[Dict[str, Any]]:
        """LF1: Exact keyword match."""
        results = []
        patterns = dynamic_db.get_rules(field)
        
        for keyword, data in patterns.items():
            if keyword.lower() in query.lower():
                results.append({
                    "value": data.get("value") or data.get("related"),
                    "confidence": data.get("confidence", 0.95),
                    "signal_type": "exact",
                    "keyword": keyword
                })
        return results

    @classmethod
    def lf_partial_match(cls, query: str, field: str) -> List[Dict[str, Any]]:
        """LF2: Partial/Sub-string match."""
        results = []
        patterns = dynamic_db.get_rules(field)
        
        for keyword, data in patterns.items():
            # If keyword is "Algorithm", we check if "Algo" is in query
            # Min length 2 or half of keyword
            min_len = max(2, len(keyword) // 2)
            if len(keyword) >= 2 and keyword[:min_len].lower() in query.lower():
                # Avoid redundancy if exact match also caught it (exact match carries higher weight)
                results.append({
                    "value": data.get("value") or data.get("related"),
                    "confidence": data.get("confidence", 0.95) * 0.7, # Lowered confidence for partial
                    "signal_type": "partial",
                    "keyword": keyword
                })
        return results

    @classmethod
    def lf_semantic_similarity(cls, query: str, field: str) -> List[Dict[str, Any]]:
        """LF3: Semantic similarity (Simplified Jaccard for now, could be vector-based)."""
        results = []
        patterns = dynamic_db.get_rules(field)
        
        query_words = set(re.findall(r"\w+", query.lower()))
        
        for keyword, data in patterns.items():
            keyword_words = set(re.findall(r"\w+", keyword.lower()))
            if not keyword_words:
                continue
            
            intersection = query_words.intersection(keyword_words)
            union = query_words.union(keyword_words)
            jaccard = len(intersection) / len(union) if union else 0
            
            if jaccard > 0.3: # Threshold
                results.append({
                    "value": data.get("value") or data.get("related"),
                    "confidence": jaccard * data.get("confidence", 0.95) * 0.5,
                    "signal_type": "semantic",
                    "keyword": keyword
                })
        return results

    @classmethod
    def aggregate_signals(cls, query: str, field: str) -> Dict[Any, float]:
        """Aggregate signals from all LFs."""
        signals = []
        signals.extend(cls.lf_exact_match(query, field))
        signals.extend(cls.lf_partial_match(query, field))
        signals.extend(cls.lf_semantic_similarity(query, field))
        
        # Group by value and take the max confidence
        val_to_conf = {}
        for sig in signals:
            val = sig["value"]
            # Convert list to tuple to make it hashable for dict keys
            if isinstance(val, list):
                val = tuple(val)
                
            conf = sig["confidence"]
            if val not in val_to_conf:
                val_to_conf[val] = []
            val_to_conf[val].append(conf)
            
        final = {v: max(confs) for v, confs in val_to_conf.items()}
        return final

    @classmethod
    def predict(cls, query: str, field: str, threshold: float = 0.4) -> Optional[Any]:
        """Predict the best value based on aggregated signals."""
        aggregated = cls.aggregate_signals(query, field)
        if not aggregated:
            return None
            
        best_val = max(aggregated, key=aggregated.get)
        confidence = aggregated[best_val]
        
        if confidence >= threshold:
            logger.debug(f"[WeakSupervision] Pred: {field}={best_val} (conf={confidence:.2f})")
            return best_val, confidence
        return None
