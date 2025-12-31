
"""
Query Reformulation Logic.
"""
from typing import List

def reformulate_query(query: str, history: List[str] = None) -> str:
    """
    Reformulate user query for better retrieval.
    Ideally uses LLM to expand/clarify.
    For now, returns query as-is or applies simple normalization.
    """
    if not query:
        return ""
        
    # Phase 2: Simple cleanup
    cleaned = query.strip()
    
    # Check history (multi-turn context)
    # This is where we'd append context if needed.
    
    return cleaned
