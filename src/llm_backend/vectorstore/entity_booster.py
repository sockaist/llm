from typing import List, Dict, Any
from llm_backend.utils.logger import logger

class EntityBooster:
    """
    Phase 7: Graph-Lite Entity Boosting.
    Identifies key entities and boosts related documents.
    """
    
    @classmethod
    def extract_entities(cls, query: str) -> List[str]:
        """Extract entities and their relations using WeakSupervisionEngine fuzzy signals."""
        from .weak_supervision import WeakSupervisionEngine
        
        # We use a lower threshold for entity extraction to allow for fuzzy matching
        res = WeakSupervisionEngine.aggregate_signals(query, "entities")
        if not res:
            return []
            
        # Filter by threshold and collect all related entities
        found_entities = []
        for val, conf in res.items():
            if conf >= 0.35: # Fuzzy trigger threshold
                if isinstance(val, (list, tuple)):
                    found_entities.extend(list(val))
                else:
                    found_entities.append(str(val))
                    
        unique_entities = list(set(found_entities))
        if unique_entities:
            logger.info(f"[EntityBoost] Predicted entities: {unique_entities}")
        return unique_entities

    @classmethod
    def apply_boost(cls, results: List[Dict[str, Any]], query_entities: List[str], boost_factor: float = 0.1) -> List[Dict[str, Any]]:
        """Apply a score boost if a result contains a query entity."""
        if not query_entities:
            return results

        logger.info(f"[EntityBoost] Boosting for entities: {query_entities}")
        for res in results:
            # Check Title, Chunk Text, and Parent Context for entities
            combined_text = (res.get("text") or "") + (res.get("title") or "") + (res.get("parent_context") or "")
            for ent in query_entities:
                if ent in combined_text:
                    res["score"] += boost_factor
                    res["avg_score"] = res.get("avg_score", 0.0) + boost_factor
                    res["_boost_reason"] = f"Matched entity: {ent}"
                    break # Apply boost once per result
        
        # Re-sort after boosting
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
