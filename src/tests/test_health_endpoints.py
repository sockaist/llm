
import sys
import os
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Patching BEFORE importing main to avoid auto-init side effects
with patch("llm_backend.server.vector_server.core.resource_pool.init_vector_pool"), \
     patch("llm_backend.server.vector_server.core.scheduler.start_scheduler"):
    from llm_backend.server.vector_server.main import app

client = TestClient(app)

def test_health_check_simple():
    """Test /health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "Vector server is alive"

@patch("llm_backend.server.vector_server.api.endpoints_health.acquire_manager")
def test_health_status(mock_acquire):
    """Test /health/status endpoint"""
    # Mock context manager return
    mock_mgr = MagicMock()
    mock_acquire.return_value.__enter__.return_value = mock_mgr
    
    # Mock qdrant call
    mock_mgr.client.get_collections.return_value = {}

    response = client.get("/health/status")
    assert response.status_code == 200
    data = response.json()
    
    assert data["server"] == "running"
    assert "resource_pool" in data
    assert "qdrant" in data
    assert data["qdrant"]["reachable"] is True
