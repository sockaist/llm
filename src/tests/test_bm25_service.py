import importlib
import json
import os
import tempfile

from llm_backend.vectorstore import sparse_helper


def test_bm25_service_init_and_fit(monkeypatch):
    # Isolate BM25_PATH to a temp file
    with tempfile.TemporaryDirectory() as tmp:
        bm25_path = os.path.join(tmp, "bm25.pkl")
        data_dir = os.path.join(tmp, "data")
        os.makedirs(data_dir, exist_ok=True)

        # write tiny corpus
        for idx, txt in enumerate(["hello world", "another doc"]):
            with open(os.path.join(data_dir, f"{idx}.json"), "w", encoding="utf-8") as fp:
                json.dump({"content": txt}, fp)

        monkeypatch.setenv("BM25_PATH", bm25_path)
        import llm_backend.vectorstore.bm25_service as bm25_service

        # Reload to pick up env override
        from llm_backend.vectorstore import config
        importlib.reload(config)
        importlib.reload(sparse_helper)
        importlib.reload(bm25_service)

        # Training should create model
        bm25_service.init_bm25(base_path=data_dir, force_retrain=True)
        assert os.path.exists(bm25_path)

        # Subsequent init should load existing model without re-training
        bm25_service.init_bm25(base_path=data_dir, force_retrain=False)
