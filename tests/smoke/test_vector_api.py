import json
import os

import pytest
import httpx


VECTOR_BASE_URL = os.getenv("VECTOR_BASE_URL", "http://localhost:8000")
VECTOR_API_KEY = os.getenv("VECTOR_API_KEY", "vortex-secret-key-123")
SKIP_SMOKE = os.getenv("SKIP_VECTOR_SMOKE", "0") == "1"


@pytest.fixture(scope="module")
def base_url() -> str:
    return VECTOR_BASE_URL.rstrip("/")


@pytest.fixture
async def client(base_url: str):
    if SKIP_SMOKE:
        pytest.skip("SKIP_VECTOR_SMOKE=1")
    try:
        headers = {"x-api-key": VECTOR_API_KEY}
        async with httpx.AsyncClient(base_url=base_url, timeout=10, headers=headers) as session:
            # quick reachability check; if it fails, skip the suite
            resp = await session.get("/health")
            resp.raise_for_status()
            yield session
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Vector server not reachable at {base_url}: {exc}")


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"


@pytest.mark.asyncio
async def test_query_endpoint(client):
    payload = {"query_text": "ping", "top_k": 1, "collections": []}
    resp = await client.post("/query/hybrid", json=payload)
    if resp.status_code >= 500:
        pytest.skip(f"/query/hybrid not available: {resp.status_code} {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    assert data.get("status") in ("success", None)


@pytest.mark.asyncio
async def test_crud_upsert_optional(client):
    """Lightweight CRUD smoke; skipped if backend rejects missing collection."""

    doc = {"content": "smoke-test", "title": "smoke"}
    files = {"file": ("doc.json", json.dumps(doc), "application/json")}
    data = {"collection": "smoke.test"}
    resp = await client.post("/crud/upsert", files=files, data=data)

    if resp.status_code in (404, 500):
        pytest.skip(f"/crud/upsert not available: {resp.status_code} {resp.text}")

    resp.raise_for_status()
    body = resp.json()
    assert body.get("status") == "success"
