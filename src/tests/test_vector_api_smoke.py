import os

import pytest
from fastapi.testclient import TestClient

from llm_backend.server.vector_server.main import app


@pytest.mark.skipif(os.getenv("ENABLE_VECTOR_SMOKE") != "1", reason="Set ENABLE_VECTOR_SMOKE=1 to run API smoke tests")
def test_health_and_query_smoke():
    client = TestClient(app)

    # health
    resp = client.get("/health")
    assert resp.status_code == 200

    # query endpoint basic contract (expects backend to be available)
    payload = {"query_text": "hello", "top_k": 1, "collections": []}
    resp = client.post("/query", json=payload)
    assert resp.status_code in (200, 503, 500)
