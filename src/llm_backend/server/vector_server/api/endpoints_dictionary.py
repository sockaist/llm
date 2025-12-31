# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel

from llm_backend.utils.logger import logger
from llm_backend.vectorstore.dynamic_db import dynamic_db
from llm_backend.server.vector_server.core.auth import verify_api_key

router = APIRouter(prefix="/dict", tags=["Dictionary"], dependencies=[Depends(verify_api_key)])

class RuleItem(BaseModel):
    keyword: str
    value: Any # Target value or list of related terms
    confidence: float = 0.5

class DictResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

@router.get("/{field}", response_model=Dict[str, Any])
async def get_dictionary(field: str):
    """
    Get all rules for a specific field (e.g., 'department', 'synonyms', 'entities').
    """
    rules = dynamic_db.get_rules(field)
    return {"field": field, "count": len(rules), "rules": rules}

@router.post("/{field}", response_model=DictResponse)
async def update_rule(field: str, item: RuleItem):
    """
    Add or Update a rule in the dictionary.
    """
    try:
        # We need to manually inject into dynamic_db rules structure
        # dynamic_db doesn't have a direct 'set_rule' method exposed cleanly other than add_feedback or manual dict manipulation.
        # Ideally, we should add a helper in dynamic_db, but for now we can manipulate the dictionary directly and save.
        
        current_rules = dynamic_db.rules.get(field)
        if current_rules is None:
            dynamic_db.rules[field] = {}
            current_rules = dynamic_db.rules[field]
            
        from datetime import datetime
        
        current_rules[item.keyword] = {
            "value": item.value,
            "confidence": item.confidence,
            "last_updated": datetime.now().isoformat(),
            "source": "manual_admin"
        }
        
        dynamic_db.save()
        logger.info(f"[API:/dict] Updated rule {field}: {item.keyword} -> {item.value}")
        
        return DictResponse(status="success", message=f"Rule '{item.keyword}' saved.")
        
    except Exception as e:
        logger.error(f"[API:/dict] Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{field}/{keyword}", response_model=DictResponse)
async def delete_rule(field: str, keyword: str):
    """
    Delete a rule from the dictionary.
    """
    try:
        if field not in dynamic_db.rules:
             raise HTTPException(status_code=404, detail=f"Field '{field}' not found")
             
        if keyword not in dynamic_db.rules[field]:
            raise HTTPException(status_code=404, detail=f"Keyword '{keyword}' not found in {field}")
            
        del dynamic_db.rules[field][keyword]
        dynamic_db.save()
        logger.info(f"[API:/dict] Deleted rule {field}: {keyword}")
        
        return DictResponse(status="success", message=f"Rule '{keyword}' deleted.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API:/dict] Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
