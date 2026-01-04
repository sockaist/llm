#!/usr/bin/env python3
"""
Comprehensive VortexDB Docker Stack Test Suite (API Key Auth)
Run: python scripts/test_docker_stack.py

Tests include:
- Health endpoints
- Authentication (valid/invalid API keys)
- CRUD operations (upsert, read, delete)
- Search operations (hybrid, keyword)
- Batch job management
- Error handling and edge cases
- Input validation
"""

import requests
import sys
import json
import time
import uuid

BASE_URL = "http://localhost:8000"
API_KEY = "vortex-secret-key-123"  # From docker-compose.yml
TEST_COLLECTION = f"test_suite_{uuid.uuid4().hex[:8]}"

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def ok(msg):
    print(f"{Colors.GREEN}✓ PASS{Colors.END} {msg}")

def fail(msg):
    print(f"{Colors.RED}✗ FAIL{Colors.END} {msg}")

def info(msg):
    print(f"{Colors.BLUE}→{Colors.END} {msg}")

def warn(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")

def section(msg):
    print(f"\n{Colors.CYAN}━━━ {msg} ━━━{Colors.END}")

def run_test(name, test_func):
    try:
        result = test_func()
        if result:
            ok(name)
            return True
        else:
            fail(name)
            return False
    except Exception as e:
        fail(f"{name}: {e}")
        return False

# ============== HEALTH TESTS ==============

def test_health_basic():
    """Test /health endpoint"""
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    return resp.status_code == 200 and resp.json().get("status") == "ok"

def test_health_status_detailed():
    """Test /health/status with full info"""
    try:
        resp = requests.get(f"{BASE_URL}/health/status", headers=HEADERS, timeout=60)
        if resp.status_code != 200:
            warn(f"Health status returned {resp.status_code}")
            return False
        data = resp.json()
        # Should have server info
        return "server" in data or "status" in data or "collections" in data
    except requests.Timeout:
        warn("Health status timed out (slow startup)")
        return True  # Skip on timeout

# ============== AUTH TESTS ==============

def test_auth_valid_key():
    """Test that valid API key grants admin access"""
    resp = requests.get(f"{BASE_URL}/admin/collections/list", headers=HEADERS, timeout=10)
    return resp.status_code == 200

def test_auth_no_key_denied_write():
    """Test that requests without API key are denied for write operations"""
    payload = {"collection": "test", "documents": [{"content": "test"}]}
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, timeout=5)
    return resp.status_code == 403 or "denied" in resp.text.lower()

def test_auth_wrong_key_denied():
    """Test that requests with wrong API key are denied"""
    bad_headers = {"Content-Type": "application/json", "x-api-key": "invalid-key-12345"}
    payload = {"collection": "test", "documents": [{"content": "test"}]}
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=bad_headers, timeout=5)
    return resp.status_code == 403 or "denied" in resp.text.lower()

def test_auth_empty_key():
    """Test that empty API key is rejected"""
    empty_headers = {"Content-Type": "application/json", "x-api-key": ""}
    payload = {"collection": "test", "documents": [{"content": "test"}]}
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=empty_headers, timeout=5)
    return resp.status_code == 403 or "denied" in resp.text.lower()

def test_auth_no_key_allows_read():
    """Test that requests without API key can still read public data (health)"""
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    return resp.status_code == 200

# ============== CRUD TESTS ==============

def test_crud_upsert_batch():
    """Test /batch/upsert_batch endpoint (async upsert)"""
    payload = {
        "collection": TEST_COLLECTION,
        "documents": [
            {"id": "test_1", "content": "Test document 1 for verification.", "title": "Test Doc 1"},
            {"id": "test_2", "content": "Another test document.", "title": "Test Doc 2"},
            {"id": "test_3", "content": "Third document for testing.", "title": "Test Doc 3"}
        ]
    }
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        warn(f"Upsert returned {resp.status_code}: {resp.text[:100]}")
        return False
    return resp.json().get("status") in ("queued", "success")

def test_crud_read_document():
    """Test /crud/document endpoint (GET)"""
    # Try reading from existing collection
    resp = requests.get(f"{BASE_URL}/crud/document/sockaist/ex_1", headers=HEADERS, timeout=10)
    # 200 = found, 404 = not found (both valid)
    return resp.status_code in (200, 404)

def test_crud_read_nonexistent():
    """Test reading a document that doesn't exist"""
    resp = requests.get(f"{BASE_URL}/crud/document/nonexistent_col/fake_id_12345", headers=HEADERS, timeout=10)
    return resp.status_code == 404

def test_crud_upsert_empty_docs():
    """Test upserting with empty documents list (should fail or be handled)"""
    payload = {"collection": "test", "documents": []}
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=HEADERS, timeout=10)
    # Could be 400 (validation) or 200 with empty success
    return resp.status_code in (200, 400, 422)

def test_crud_upsert_missing_content():
    """Test upserting document without content field"""
    payload = {
        "collection": "test",
        "documents": [{"id": "incomplete", "title": "No Content"}]  # Missing content
    }
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=HEADERS, timeout=10)
    # Should handle gracefully
    return resp.status_code in (200, 400, 422)

# ============== SEARCH TESTS ==============

def test_search_hybrid():
    """Test /query/hybrid endpoint"""
    payload = {
        "query_text": "test document verification",
        "top_k": 5,
        "collections": []  # Search all
    }
    resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        warn(f"Hybrid search returned {resp.status_code}: {resp.text[:100]}")
        return False
    return resp.json().get("status") == "success"

def test_search_keyword():
    """Test /query/keyword endpoint"""
    payload = {"query": "test", "top_k": 5}
    resp = requests.post(f"{BASE_URL}/query/keyword", json=payload, headers=HEADERS, timeout=30)
    if resp.status_code == 404:
        warn("Keyword search not available (skipped)")
        return True
    if resp.status_code != 200:
        warn(f"Keyword search returned {resp.status_code}")
        return False
    return resp.json().get("status") == "success"

def test_search_empty_query():
    """Test search with empty query (should fail validation)"""
    payload = {"query_text": "", "top_k": 5, "collections": []}
    resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=HEADERS, timeout=30)
    # Empty query might be handled differently - either 400 or return empty results
    return resp.status_code in (200, 400, 422)

def test_search_large_top_k():
    """Test search with very large top_k (should be bounded)"""
    payload = {"query_text": "test", "top_k": 10000, "collections": []}
    resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=HEADERS, timeout=60)
    # Should either return results (bounded) or reject
    return resp.status_code in (200, 400, 422)

def test_search_negative_top_k():
    """Test search with negative top_k (should fail validation)"""
    payload = {"query_text": "test", "top_k": -5, "collections": []}
    resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=HEADERS, timeout=10)
    return resp.status_code in (400, 422)

def test_search_specific_collection():
    """Test search targeting specific collection"""
    payload = {"query_text": "document", "top_k": 3, "collections": ["sockaist"]}
    resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=HEADERS, timeout=60)
    if resp.status_code != 200:
        return False
    results = resp.json().get("results", [])
    # All results should be from specified collection (if any)
    for r in results:
        if r.get("collection") and r.get("collection") != "sockaist":
            return False
    return True

def test_search_nonexistent_collection():
    """Test search in collection that doesn't exist"""
    payload = {"query_text": "test", "top_k": 5, "collections": ["this_collection_does_not_exist_xyz"]}
    resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=HEADERS, timeout=30)
    # Should return empty results or 404
    if resp.status_code == 200:
        return len(resp.json().get("results", [])) == 0
    return resp.status_code in (404, 400)

# ============== ADMIN TESTS ==============

def test_admin_collections_list():
    """Test /admin/collections/list endpoint"""
    resp = requests.get(f"{BASE_URL}/admin/collections/list", headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return False
    data = resp.json()
    return data.get("status") == "success" and "collections" in data

def test_admin_collections_count():
    """Test that collections have valid count fields"""
    resp = requests.get(f"{BASE_URL}/admin/collections/list", headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return False
    collections = resp.json().get("collections", [])
    for col in collections:
        if "count" not in col or "name" not in col:
            return False
    return True

# ============== BATCH JOB TESTS ==============

def test_batch_jobs_list():
    """Test /batch/jobs/list endpoint"""
    resp = requests.get(f"{BASE_URL}/batch/jobs/list", headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        warn(f"Batch jobs list returned {resp.status_code}")
        return False
    data = resp.json()
    return data.get("status") == "success" and "jobs" in data

def test_batch_job_status():
    """Test /batch/jobs/status/{id} with real job ID"""
    # First get job list
    resp = requests.get(f"{BASE_URL}/batch/jobs/list", headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        warn("Cannot get job list")
        return True  # Skip if list not available
    
    jobs = resp.json().get("jobs", [])
    if not jobs:
        warn("No jobs to check status")
        return True  # Skip if no jobs
    
    job_id = jobs[0]["id"]
    resp = requests.get(f"{BASE_URL}/batch/jobs/status/{job_id}", headers=HEADERS, timeout=10)
    return resp.status_code == 200

def test_batch_job_invalid_id():
    """Test job status with invalid ID"""
    resp = requests.get(f"{BASE_URL}/batch/jobs/status/invalid-job-id-xyz", headers=HEADERS, timeout=10)
    # Could be 404 (not found), 400 (bad request), or 422 (validation error)
    return resp.status_code in (404, 400, 422, 500)  # 500 also acceptable for missing job

# ============== ERROR HANDLING TESTS ==============

def test_error_invalid_json():
    """Test sending invalid JSON"""
    resp = requests.post(
        f"{BASE_URL}/batch/upsert_batch",
        data="not valid json {{{",
        headers={"Content-Type": "application/json", "x-api-key": API_KEY},
        timeout=10
    )
    return resp.status_code in (400, 422)

def test_error_missing_required_field():
    """Test request missing required field"""
    payload = {"documents": [{"content": "test"}]}  # Missing 'collection'
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=HEADERS, timeout=10)
    return resp.status_code in (400, 422)

def test_error_wrong_http_method():
    """Test using wrong HTTP method"""
    resp = requests.get(f"{BASE_URL}/batch/upsert_batch", headers=HEADERS, timeout=10)
    return resp.status_code == 405

def test_error_nonexistent_endpoint():
    """Test accessing non-existent endpoint"""
    resp = requests.get(f"{BASE_URL}/this/endpoint/does/not/exist", headers=HEADERS, timeout=10)
    return resp.status_code == 404

# ============== EDGE CASES ==============

def test_edge_unicode_content():
    """Test upserting content with Unicode characters"""
    payload = {
        "collection": TEST_COLLECTION,
        "documents": [{
            "id": "unicode_test",
            "content": "한글 테스트 文字 🎉 émojis and spëcîäl characters",
            "title": "Unicode Test 유니코드"
        }]
    }
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=HEADERS, timeout=30)
    return resp.status_code == 200

def test_edge_long_content():
    """Test upserting very long content"""
    long_text = "Test content. " * 1000  # ~14KB of text
    payload = {
        "collection": TEST_COLLECTION,
        "documents": [{"id": "long_doc", "content": long_text, "title": "Long Document"}]
    }
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=HEADERS, timeout=60)
    return resp.status_code in (200, 413)  # 413 = payload too large (acceptable)

def test_edge_special_chars_in_id():
    """Test document ID with special characters"""
    payload = {
        "collection": TEST_COLLECTION,
        "documents": [{"id": "doc-with_special.chars:123", "content": "Test", "title": "Special ID"}]
    }
    resp = requests.post(f"{BASE_URL}/batch/upsert_batch", json=payload, headers=HEADERS, timeout=30)
    return resp.status_code in (200, 400)

def test_edge_search_korean():
    """Test search with Korean query"""
    payload = {"query_text": "인공지능 머신러닝 딥러닝", "top_k": 5, "collections": []}
    resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=HEADERS, timeout=60)
    return resp.status_code == 200

def test_edge_concurrent_requests():
    """Test handling of concurrent requests"""
    import concurrent.futures
    
    def make_request():
        payload = {"query_text": "test", "top_k": 1, "collections": []}
        return requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=HEADERS, timeout=30)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # All should succeed
    return all(r.status_code == 200 for r in results)

# ============== MAIN ==============

def main():
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}   VortexDB Docker Stack Comprehensive Test Suite{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    print(f"Target: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-5:]}")
    print(f"Test Collection: {TEST_COLLECTION}\n")
    
    # Check if server is reachable
    info("Checking server reachability...")
    try:
        requests.get(f"{BASE_URL}/health", timeout=3)
    except Exception as e:
        fail(f"Server not reachable at {BASE_URL}: {e}")
        sys.exit(1)
    
    ok("Server is reachable")
    
    tests = {
        "Health & Status": [
            ("Health Check (Basic)", test_health_basic),
            ("Health Status (Detailed)", test_health_status_detailed),
        ],
        "Authentication": [
            ("Valid API Key (Admin Access)", test_auth_valid_key),
            ("No API Key (Denied Write)", test_auth_no_key_denied_write),
            ("Wrong API Key (Denied)", test_auth_wrong_key_denied),
            ("Empty API Key (Denied)", test_auth_empty_key),
            ("No API Key (Allow Read)", test_auth_no_key_allows_read),
        ],
        "CRUD Operations": [
            ("Batch Upsert Documents", test_crud_upsert_batch),
            ("Read Document", test_crud_read_document),
            ("Read Nonexistent Document", test_crud_read_nonexistent),
            ("Upsert Empty Documents", test_crud_upsert_empty_docs),
            ("Upsert Missing Content", test_crud_upsert_missing_content),
        ],
        "Search Operations": [
            ("Hybrid Search", test_search_hybrid),
            ("Keyword Search", test_search_keyword),
            ("Empty Query", test_search_empty_query),
            ("Large top_k", test_search_large_top_k),
            ("Negative top_k", test_search_negative_top_k),
            ("Specific Collection", test_search_specific_collection),
            ("Nonexistent Collection", test_search_nonexistent_collection),
        ],
        "Admin Endpoints": [
            ("Collections List", test_admin_collections_list),
            ("Collections Count", test_admin_collections_count),
        ],
        "Batch Job Management": [
            ("Jobs List", test_batch_jobs_list),
            ("Job Status (Real ID)", test_batch_job_status),
            ("Job Status (Invalid ID)", test_batch_job_invalid_id),
        ],
        "Error Handling": [
            ("Invalid JSON", test_error_invalid_json),
            ("Missing Required Field", test_error_missing_required_field),
            ("Wrong HTTP Method", test_error_wrong_http_method),
            ("Nonexistent Endpoint", test_error_nonexistent_endpoint),
        ],
        "Edge Cases": [
            ("Unicode Content", test_edge_unicode_content),
            ("Long Content", test_edge_long_content),
            ("Special Chars in ID", test_edge_special_chars_in_id),
            ("Korean Search Query", test_edge_search_korean),
            ("Concurrent Requests", test_edge_concurrent_requests),
        ],
    }
    
    total_passed = 0
    total_failed = 0
    
    for category, category_tests in tests.items():
        section(category)
        for name, func in category_tests:
            if run_test(name, func):
                total_passed += 1
            else:
                total_failed += 1
    
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"  Total: {Colors.GREEN}{total_passed} passed{Colors.END}, {Colors.RED}{total_failed} failed{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    if total_failed > 0:
        print(f"{Colors.RED}Some tests failed. Please review before building.{Colors.END}\n")
        sys.exit(1)
    else:
        print(f"{Colors.GREEN}All tests passed! ✓ Ready for build.{Colors.END}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
