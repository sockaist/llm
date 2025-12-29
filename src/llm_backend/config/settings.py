# Default configuration for hybrid search and reranking pipeline

PIPELINE_CONFIG = {
    # Feature Flags
    "use_dense": True,
    "use_sparse": True,
    "use_splade": True,
    "use_reranker": True,
    "use_date_boost": True,

    # Fusion Weights (RRF / Weighted Sum)
    "dense_weight": 0.6,
    "sparse_weight": 0.3,
    "splade_weight": 0.1,

    # Model Settings
    "cross_encoder_model": "Dongjin-kr/ko-reranker",

    # Date Boosting Settings
    "date_decay_rate": 0.03,
    "date_weight": 0.45,
    "date_from": None,
    "date_to": None,
}
