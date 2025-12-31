from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from llm_backend.vectorstore.search_pipeline import run_query_pipeline

class Hit(dict):
    def __init__(self, id, score=1.0, **kwargs):
        super().__init__(id=id, db_id=id, score=score, avg_score=score, payload={}, **kwargs)
        self.id = id
        self.score = score
        self.payload = {}
        for k, v in kwargs.items():
            setattr(self, k, v)

class DummyManager:
    def __init__(self):
        self.client = MagicMock()
        self.default_collection = "c1"
        self.dense_model = SimpleNamespace(encode=lambda text: [0.1] * 1024)

@patch("llm_backend.vectorstore.search_pipeline.q_unique")
def test_pipeline_without_reranker_returns_fused(mock_q_unique):
    # Mock return values for q_unique
    # It returns list of dicts.
    mock_q_unique.return_value = [
        Hit(id="doc1", score=1.0, text="hello world", title="t1")
    ]
    
    mgr = DummyManager()
    cfg = {
        "use_dense": True,
        "use_sparse": True,
        "use_splade": False,
        "dense_weight": 0.6,
        "sparse_weight": 0.4,
        "splade_weight": 0.0,
        "use_reranker": False,
        "cross_encoder_model": "stub",
        "use_date_boost": False,
        "date_from": None,
        "date_to": None,
        "date_decay_rate": 0.03,
        "date_weight": 0.45,
    }

    results = run_query_pipeline(
        manager=mgr,
        query_text="hello",
        top_k=5,
        collections=["c1"],
        cfg=cfg,
    )

    assert len(results) == 1
    assert results[0]["avg_score"] >= 0
