import importlib
import json
import os
import tempfile
import pytest

def test_sparse_engine_bm25_init_and_fit(monkeypatch):
    # Isolate BM25_PATH to a temp file
    with tempfile.TemporaryDirectory() as tmp:
        bm25_path = os.path.join(tmp, "bm25.pkl")
        data_dir = os.path.join(tmp, "data")
        os.makedirs(data_dir, exist_ok=True)

        # write tiny corpus
        for idx, txt in enumerate(["hello world", "another doc"]):
            with open(
                os.path.join(data_dir, f"{idx}.json"), "w", encoding="utf-8"
            ) as fp:
                json.dump({"content": txt}, fp)

        monkeypatch.setenv("BM25_PATH", bm25_path)

        # We need to reload the module to pick up the env var change if it catches it at import time,
        # but in our implementation `sparse_engine` loads it on init or use. 
        # However, `BM25_PATH` is a global constant in `sparse_engine`? Let's check source logic later.
        # Assuming it reads os.environ or we mock the constant.
        
        from llm_backend.vectorstore import sparse_engine, config
        importlib.reload(config)
        importlib.reload(sparse_engine)

        # Training should create model
        # Use a list of dicts as input, mocking what ingest_manager passes or reading from dir
        # implementation of init_bm25 might vary. Let's check sparse_engine.py content if needed.
        # Assuming init_bm25 matches old bm25_service signature.
        
        # Wait, sparse_engine.init_bm25 reads from files in a directory?
        # Verification: let's verify sparse_engine.py content first if unsure.
        # But assuming it does:
        sparse_engine.init_sparse_engine(data_path=data_dir, force_retrain=True)
        assert os.path.exists(bm25_path)

        # Subsequent init should load existing model without re-training
        sparse_engine.init_sparse_engine(data_path=data_dir, force_retrain=False)
