from types import SimpleNamespace

from llm_backend.vectorstore.search_pipeline import run_query_pipeline


class Hit(SimpleNamespace):
    pass


class DummyManager:
    def __init__(self):
        self.client = None
        self.default_collection = "c1"

    def _search_collection_unique(self, col, query_text, top_k, use_dense, use_sparse, use_splade):
        dense = [Hit(id="doc1", score=1.0)]
        sparse = [Hit(id="doc1", score=0.5)]
        splade = []
        return dense, sparse, splade


def test_pipeline_without_reranker_returns_fused():
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
