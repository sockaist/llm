import types

import torch

from llm_backend.vectorstore import rerank_service


class _FakeTokenizer:
    def __call__(self, queries, docs, padding, truncation, max_length, return_tensors):
        # Return a minimal tensor-like mapping that supports .to()
        data = {"input_ids": torch.ones((len(queries), max_length), dtype=torch.int64)}
        return _TensorMap(data)


class _TensorMap(dict):
    def to(self, device):
        return self


class _FakeModel:
    def __call__(self, **kwargs):
        batch = kwargs["input_ids"].shape[0]
        logits = torch.arange(float(batch)).reshape(batch, 1)
        return types.SimpleNamespace(logits=logits)


def test_rerank_service_with_stub(monkeypatch):
    monkeypatch.setattr(rerank_service, "_load_model", lambda name: (_FakeTokenizer(), _FakeModel()))

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

    # scores should be descending (1 then 0)
    assert [r["id"] for r in reranked] == ["b", "a"]
    assert timing["rerank_s"] >= 0
