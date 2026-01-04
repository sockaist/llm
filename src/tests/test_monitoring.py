import sys
import os
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure src in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Patch start_scheduler, init_vector_pool to avoid real startup
with (
    patch("llm_backend.server.vector_server.core.resource_pool.init_vector_pool"),
    patch("llm_backend.server.vector_server.core.scheduler.start_scheduler"),
):
    from llm_backend.server.vector_server.main import app
    from llm_backend.server.vector_server.core.canary_manager import CanaryManager

client = TestClient(app)


def test_metrics_endpoint():
    """Verify /metrics endpoint exposes Prometheus data."""
    # Note: Instrumentator usually exposes on startup.
    # We also added a manual route in endpoints_metrics just in case, or to confirm.
    response = client.get("/metrics")
    assert response.status_code == 200
    # Check for basic Prometheus format
    assert "# HELP" in response.text
    assert "# TYPE" in response.text
    assert "http_requests_total" in response.text


def test_canary_logic():
    """Verify CanaryManager logic."""
    mgr = CanaryManager.get_instance()

    # 1. Default (percentage=0) -> False
    mgr.canary_percentage = 0
    assert mgr.is_active(headers={}) is False

    # 2. Header Force -> True
    assert mgr.is_active(headers={"x-canary": "true"}) is True

    # 3. Percentage = 100 -> True
    mgr.canary_percentage = 100
    assert mgr.is_active(headers={}) is True

    # 4. Deterministic User logic
    mgr.canary_percentage = 50
    # We can't easily mock inner hash without knowing algo.
    # But same user should get same result.
    res1 = mgr.is_active(user_context={"user_id": "fixed_user"})
    res2 = mgr.is_active(user_context={"user_id": "fixed_user"})
    assert res1 == res2, "Canary should be deterministic for same user"


if __name__ == "__main__":
    test_metrics_endpoint()
    test_canary_logic()
    print("[OK] Monitoring & Canary Tests Passed")
