
import sys
import os
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Patching BEFORE importing main to avoid auto-init side effects if any
with patch("llm_backend.server.vector_server.core.resource_pool.init_vector_pool"), \
     patch("llm_backend.server.vector_server.core.scheduler.start_scheduler"):
    from llm_backend.server.vector_server.main import app

client = TestClient(app)

# Mock headers
ADMIN_HEADERS = {"X-User-ID": "admin_u", "X-Role": "admin"}
USER_HEADERS = {"X-User-ID": "user_a", "X-Role": "user"}
GUEST_HEADERS = {"X-User-ID": "guest_u", "X-Role": "guest"}

@patch("llm_backend.server.vector_server.api.endpoints_query.acquire_manager")
def test_search_context_passing(mock_acquire):
    # Setup Mock
    mock_mgr = MagicMock()
    mock_acquire.return_value.__enter__.return_value = mock_mgr
    
    # query_hybrid mocks
    mock_mgr.query.return_value = []
    
    # 1. Test Admin Search
    payload = {"query_text": "test", "top_k": 5}
    client.post("/query/hybrid", json=payload, headers=ADMIN_HEADERS)
    
    # Check call args
    args, kwargs = mock_mgr.query.call_args
    assert kwargs.get("user_context") == {"user_id": "admin_u", "role": "admin"}
    
    # 2. Test User Search
    client.post("/query/hybrid", json=payload, headers=USER_HEADERS)
    args, kwargs = mock_mgr.query.call_args
    assert kwargs.get("user_context") == {"user_id": "user_a", "role": "user"}

@patch("llm_backend.server.vector_server.api.endpoints_crud.acquire_manager")
def test_upsert_enforcement(mock_acquire):
    # Setup Mock
    mock_mgr = MagicMock()
    mock_acquire.return_value.__enter__.return_value = mock_mgr
    
    file_content = json.dumps({
        "content": "Secret Data",
        "tenant_id": "public",  # Attempt to spoil public
        "access_level": 1
    }).encode("utf-8")
    
    files = {"file": ("doc.json", file_content, "application/json")}
    
    # 1. Test User Upsert (Should OVERRIDE tenant_id)
    client.post("/crud/upsert", data={"collection": "test"}, files=files, headers=USER_HEADERS)
    
    args, kwargs = mock_mgr.upsert_document.call_args
    # args: (collection, data)
    data_arg = args[1]
    assert data_arg["tenant_id"] == "user_a", "User upsert MUST be forced to user_id!"
    
    # 2. Test Admin Upsert (Should RESPECT tenant_id)
    # Re-create file generator
    files = {"file": ("doc.json", file_content, "application/json")}
    client.post("/crud/upsert", data={"collection": "test"}, files=files, headers=ADMIN_HEADERS)
    
    args, kwargs = mock_mgr.upsert_document.call_args
    data_arg = args[1]
    assert data_arg["tenant_id"] == "public", "Admin upsert should allow public tenant_id"

if __name__ == "__main__":
    # Manually run if executed as script
    # But usually via pytest
    print("Run via pytest!")
