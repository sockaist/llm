from llm_backend.utils.logger import logger
from .adaptive_fusion import analyze_query_type


def get_optimized_hp(query_text: str, current_cfg: dict) -> dict:
    """
    Phase 5: AutoRAG-HP (Online Hyper-param Tuning)
    Determines optimal search weights and k based on query intent.
    """
    # 1. Base intent from adaptive_fusion
    dynamic_weights = analyze_query_type(query_text)

    hp = {
        "dense_weight": dynamic_weights["dense_weight"],
        "sparse_weight": dynamic_weights["sparse_weight"],
        "splade_weight": dynamic_weights["splade_weight"],
        "title_weight": 0.2,  # Default
        "search_k": 50,  # Base search depth
    }

    query_lower = query_text.lower()

    # 2. Heuristics for specialized HP
    # Strategy C: KAIST CS & Internal Administrative (REFINED)
    if any(
        kw in query_lower
        for kw in [
            "전산학부",
            "학사",
            "졸업",
            "이수",
            "교과목",
            "수강",
            "학위",
            "학번",
            "장학",
            "총장",
        ]
    ):
        hp["title_weight"] = 0.8
        hp["dense_weight"] = 0.2
        hp["search_k"] = 40  # Precise administrative lookup
        logger.info("[AutoRAG-HP] Strategy: KAIST Internal/Admin (Title Centric)")

    # Strategy A: Faculty/Staff/Identity Search
    elif any(
        kw in query_lower
        for kw in ["학과", "연락처", "교수", "누구", "전화", "이메일", "성함", "오시는"]
    ):
        hp["title_weight"] = 0.7
        hp["dense_weight"] = 0.2
        hp["search_k"] = 30
        logger.info("[AutoRAG-HP] Strategy: KAIST Identity/Contact (Title Boosted)")

    # Strategy B: Research/Tech Topical Search
    elif any(
        kw in query_lower
        for kw in ["동향", "설명", "알려줘", "무엇", "기술", "연구", "논문", "발표"]
    ):
        hp["splade_weight"] += 0.15
        hp["dense_weight"] += 0.1
        hp["search_k"] = 100  # High recall for research/tech deep dive
        logger.info("[AutoRAG-HP] Strategy: KAIST CS Research (Recall Expanded)")

    # 3. Apply user overrides from current_cfg
    final_hp = {**hp}
    for key in hp:
        if key in current_cfg:
            final_hp[key] = current_cfg[key]

    return final_hp
