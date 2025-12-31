from typing import List, Dict, Any, Optional
from .search_pipeline import run_query_pipeline
from .metadata_router import MetadataRouter
from .dynamic_db import dynamic_db
from llm_backend.utils.logger import logger

class DualPathOrchestrator:
    """
    Phase 8: Dual-Path Orchestrator.
    Separates Deterministic (Metadata) and Semantic (Vector) results.
    """

    @classmethod
    def process_query(cls, manager, query_text: str, top_k: int = 5, collections: Optional[List[str]] = None,
                      user_context: Optional[Dict[str, Any]] = None,
                      pipeline_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes both paths and combines results.
        Accepted overrides: alpha, tuning_mode, etc.
        """
        logger.info(f"[DualPath] Processing query: '{query_text}' (User: {user_context.get('user_id') if user_context else 'None'})")
        
        cfg = manager.pipeline_config.copy()
        if pipeline_overrides:
             cfg.update(pipeline_overrides)
        collections = collections or [manager.default_collection]
        
        # 1. Deterministic/Primary Path (Metadata Routing)
        # Note: In a real LLM-backed system, we'd use LLM here to extract structured metadata.
        # For now, we use our Fuzzy MetadataRouter.
        query_filters = MetadataRouter.extract_filters(query_text)
        
        # 2. Semantic Path (Standard Pipeline with Original Query)
        # We pass the filters to the pipeline to narrow search, but preserve the original text for encoding.
        semantic_results = run_query_pipeline(
            manager=manager,
            query_text=query_text, # Original Query Preserved
            top_k=top_k,
            collections=collections,
            cfg=cfg,
            user_context=user_context
        )
        
        # 3. Identify "Primary" vs "Recommendations" & Tune Confidence
        # If we have a very high confidence metadata match, we can flag those results as Primary.
        # We also tune the confidence score based on the strategy requested.
        
        if query_filters:
            [r for r in semantic_results if r.get("score_breakdown", {}).get("is_filtered", False)]
            for r in semantic_results:
                r["path_type"] = "primary"
        else:
             for r in semantic_results:
                r["path_type"] = "recommendation"

        # Apply Confidence Tuning (User Request: Weighted Average Strategy)
        for r in semantic_results:
            # Get base scores
            vector_score = r.get("score", 0.0)
            hard_score = 0.95 if query_filters else 0.5  # Assumed high confidence if metadata matched
            
            # Explicit Formula: max(hard*0.4 + vector*0.6, 0.5) if hit likely
            # Since we don't know Hit@K per query at runtime without ground truth, we prioritize strict logic.
            # If metadata filter applied, we trust it more.
            
            if query_filters:
                 # High trust in hard filters
                 tuned_conf = (hard_score * 0.4) + (vector_score * 0.6)
                 tuned_conf = max(tuned_conf, 0.65) # Minimum confidence for filtered results
            else:
                 # Vector only
                 tuned_conf = vector_score # Keep as is, or slight boost?
                 # Let's apply specific formula from request for "Vector Only" case if we assume 'hard' is low
                 tuned_conf = (0.5 * 0.4) + (vector_score * 0.6) # Blending with neutral hard score
            
            # Cap at 1.0
            r["original_score"] = vector_score
            r["score"] = min(1.0, tuned_conf)
            r["confidence"] = r["score"] # Alias for UI

        return {
            "query": query_text,
            "results": semantic_results,
            "metadata_applied": True if query_filters else False,
            "debug": {
                "filters": str(query_filters) if query_filters else None
            }
        }

    @classmethod
    def apply_feedback(cls, query: str, user_action: Dict[str, Any], path_type: str, 
                       field: Optional[str] = None, target_value: Any = None):
        """
        Phase 8.1: Apply validated feedback to both paths.
        - Primary Path: Updates confidence in DynamicRuleDB with Validator & Decay.
        - Semantic Path: Influences future ranking (e.g., via Bandit rewards).
        """
        from .feedback_validator import FeedbackValidator
        
        # 1. Validate feedback quality (Phase 8.1)
        is_valid, validator_conf = FeedbackValidator.validate(user_action)
        if not is_valid:
            return

        feedback_type = user_action.get("explicit", "neutral")
        score = 1.0 if feedback_type == "positive" else -1.0 if feedback_type == "negative" else 0.0
        
        logger.info(f"[DualPath] Applying {feedback_type} feedback ({validator_conf}) for '{query}' -> {path_type}")
        
        if path_type == "primary" and field and target_value:
            # Update the dynamic rule DB using keywords from the original query
            dynamic_db.add_feedback(
                field=field,
                query=query,
                value=target_value,
                feedback_score=score,
                validator_conf=validator_conf
            )
        
        # 2. Update Semantic Path (Bandit rewards)
        # manager.bandit_tuner.update_reward(query, score)
