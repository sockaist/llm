"""Dynamic weight adjustment for Hybrid Search based on query analysis."""

from typing import Dict


def analyze_query_type(query: str) -> Dict[str, float]:
    """
    Analyze query to determine weights for Dense, Sparse, and SPLADE.
    """
    query = query.strip()
    words = query.split()
    word_count = len(words)

    # Default weights
    weights = {"dense_weight": 0.5, "sparse_weight": 0.3, "splade_weight": 0.2}

    # 1. Short keyword-heavy query (e.g. "AI Research", "NLP")
    if word_count <= 3:
        weights["dense_weight"] = 0.3
        weights["sparse_weight"] = 0.5
        weights["splade_weight"] = 0.2

    # 2. Long descriptive query (e.g. "What are the latest trends in autonomous driving research at KAIST?")
    elif word_count >= 8:
        weights["dense_weight"] = 0.6
        weights["sparse_weight"] = 0.15
        weights["splade_weight"] = 0.25

    # 3. Middle range or specific markers
    else:
        # Check for specific intent (to be expanded)
        if "?" in query or "how" in query.lower() or "why" in query.lower():
            weights["dense_weight"] = 0.6
            weights["sparse_weight"] = 0.1
            weights["splade_weight"] = 0.3

    return weights
