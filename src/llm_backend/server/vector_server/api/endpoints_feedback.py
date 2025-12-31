# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from llm_backend.utils.logger import logger
from llm_backend.vectorstore.dual_path import DualPathOrchestrator
from llm_backend.vectorstore.metrics_collector import MetricsCollector

router = APIRouter(prefix="/feedback", tags=["Feedback"])

class FeedbackRequest(BaseModel):
    query: str = Field(..., description="Original user query")
    action_type: str = Field(..., description="Type of action: click, like, dislike")
    target_id: Optional[str] = Field(None, description="ID of the document interacted with")
    path_type: str = Field("recommendation", description="Source path: primary or recommendation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context (dwell_time, user_id)")
    
    # Optional fields for learning
    field: Optional[str] = Field(None, description="Target field for rule update (e.g., category)")
    value: Optional[Any] = Field(None, description="Target value for rule update")

class FeedbackResponse(BaseModel):
    status: str
    message: str
    validator_confidence: Optional[str] = None

@router.post("", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
    """
    Submit user feedback for a query result.
    Triggers 'DualPathOrchestrator.apply_feedback' to update dynamic rules or bandit weights.
    """
    try:
        # Construct user_action dictionary for internal use
        user_action = {
            "explicit": "positive" if req.action_type in ["like", "click"] else "negative",
            "dwell_time": req.metadata.get("dwell_time", 0),
            "user_id": req.metadata.get("user_id", "anonymous"),
            "is_duplicate": False, # TODO: Implement session-based duplicate check
            "is_bot": False        # TODO: Implement basic bot check middleware
        }
        
        # Apply feedback logic
        # this returns None, but logs internally and updates DB if valid
        # We might want to capture the validator confidence from within, but for now apply_feedback doesn't return it easily.
        # We can re-validate here if we want the status code, or trust the orchestrator logs.
        # Let's peek at validator first for response clarity.
        
        from llm_backend.vectorstore.feedback_validator import FeedbackValidator
        is_valid, conf = FeedbackValidator.validate(user_action)
        
        if not is_valid:
            logger.warning(f"[API:/feedback] Feedback rejected ({conf}) for '{req.query}'")
            return FeedbackResponse(status="ignored", message="Low quality feedback rejected", validator_confidence=conf)

        # Proceed to update
        DualPathOrchestrator.apply_feedback(
            query=req.query, 
            user_action=user_action, 
            path_type=req.path_type,
            field=req.field, 
            target_value=req.value
        )
        
        return FeedbackResponse(
            status="success", 
            message="Feedback processed", 
            validator_confidence=conf
        )

    except Exception as e:
        logger.error(f"[API:/feedback] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, Any])
async def get_feedback_stats():
    """
    Retrieve system-wide feedback and rule statistics.
    """
    try:
        return MetricsCollector.get_rule_stats()
    except Exception as e:
        logger.error(f"[API:/feedback/stats] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
