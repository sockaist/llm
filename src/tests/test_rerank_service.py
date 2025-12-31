
import torch

from llm_backend.vectorstore import rerank_service


class _FakeCrossEncoder:
    def predict(self, pairs, show_progress_bar=False):
        # Return fake scores for each pair
        # pairs is list of (query, text)
        return torch.tensor([float(i) for i in range(len(pairs))], dtype=torch.float32)

def test_rerank_service_with_stub(monkeypatch):
    # Mock _load_model to return a FakeCrossEncoder
    monkeypatch.setattr(rerank_service, "_load_model", lambda name: _FakeCrossEncoder())

    docs = [
        {"id": "a", "text": "hello", "title": "t1"},
        {"id": "b", "text": "world", "title": "t2"},
    ]

    reranked, timing = rerank_service.rerank(
        query="q",
        docs=docs,
        model_name="stub-model",
        top_k=2,
        device="cpu",
    )

    # _FakeCrossEncoder returns scores [0.0, 1.0] for input pairs
    # Index 0 (doc 'a') gets 0.0
    # Index 1 (doc 'b') gets 1.0
    # So 'b' should be first.
    assert [r["id"] for r in reranked] == ["b", "a"]
    assert timing["rerank_s"] >= 0
