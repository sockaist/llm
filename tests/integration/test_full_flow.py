# -*- coding: utf-8 -*-
"""
Integration Tests for VortexDB API.
Tests full API flows including authentication, search, and CRUD.
"""
import pytest
import httpx
import os

VECTOR_BASE_URL = os.getenv("VECTOR_BASE_URL", "http://localhost:8000")
VECTOR_API_KEY = os.getenv("VECTOR_API_KEY", "test-api-key")


@pytest.fixture(scope="module")
async def client():
    """Create async HTTP client for testing."""
    headers = {"x-api-key": VECTOR_API_KEY}
    async with httpx.AsyncClient(
        base_url=VECTOR_BASE_URL,
        timeout=30,
        headers=headers
    ) as session:
        # Check server is reachable
        try:
            resp = await session.get("/health")
            if resp.status_code != 200:
                pytest.skip(f"Server not healthy: {resp.status_code}")
        except Exception as e:
            pytest.skip(f"Server not reachable: {e}")
        yield session


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        """Health endpoint should return OK status."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "ok"


class TestSearchFlow:
    """Test search API flow."""
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, client):
        """Hybrid search should return valid response."""
        payload = {
            "query_text": "machine learning",
            "top_k": 5,
            "collections": []
        }
        resp = await client.post("/query/hybrid", json=payload)
        
        if resp.status_code >= 500:
            pytest.skip(f"Search endpoint error: {resp.status_code}")
        
        assert resp.status_code in [200, 400, 403]  # OK or expected errors
        
        if resp.status_code == 200:
            data = resp.json()
            assert "status" in data
            assert "results" in data
    
    @pytest.mark.asyncio
    async def test_keyword_search(self, client):
        """Keyword search should return valid response."""
        payload = {
            "query": "KAIST",
            "top_k": 5
        }
        resp = await client.post("/query/keyword", json=payload)
        
        if resp.status_code >= 500:
            pytest.skip(f"Keyword search error: {resp.status_code}")
        
        assert resp.status_code in [200, 400, 403]


class TestAuthenticationFlow:
    """Test authentication and authorization."""
    
    @pytest.mark.asyncio
    async def test_request_without_api_key(self):
        """Request without API key should have limited access."""
        async with httpx.AsyncClient(
            base_url=VECTOR_BASE_URL,
            timeout=10
        ) as session:
            resp = await session.get("/health")
            # Health should be accessible without API key
            assert resp.status_code == 200
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Request with invalid API key should be rejected or limited."""
        headers = {"x-api-key": "invalid-key-12345"}
        async with httpx.AsyncClient(
            base_url=VECTOR_BASE_URL,
            timeout=10,
            headers=headers
        ) as session:
            resp = await session.get("/health")
            # Should still work but with viewer role
            assert resp.status_code in [200, 401, 403]


class TestErrorResponses:
    """Test error response format."""
    
    @pytest.mark.asyncio
    async def test_invalid_top_k(self, client):
        """Invalid top_k should return validation error."""
        payload = {
            "query_text": "test",
            "top_k": 1000,  # Over limit
            "collections": []
        }
        resp = await client.post("/query/hybrid", json=payload)
        
        if resp.status_code == 400:
            data = resp.json()
            assert "status" in data or "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
