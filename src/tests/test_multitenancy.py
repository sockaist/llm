import sys
import os
import time
import pytest

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from llm_backend.vectorstore.vector_db_manager import VectorDBManager
from llm_backend.vectorstore.search_pipeline import run_query_pipeline

COLLECTION = "test.multitenancy"


@pytest.fixture
def manager():
    mgr = VectorDBManager()
    # Setup Data
    print(f"\n[Setup] Creating collection {COLLECTION}...", flush=True)
    mgr.create_collection(COLLECTION, vector_size=1024, force=True)

    docs = [
        {
            "id": "doc_public",
            "content": "This is public information.",
            "tenant_id": "public",
            "access_level": 1,
        },
        {
            "id": "doc_user_a",
            "content": "This is User A's private note.",
            "tenant_id": "user_a",
            "access_level": 1,
        },
        {
            "id": "doc_user_b",
            "content": "This is User B's private note.",
            "tenant_id": "user_b",
            "access_level": 1,
        },
        {
            "id": "doc_admin",
            "content": "This is Top Secret Admin data.",
            "tenant_id": "public",
            "access_level": 3,
        },
    ]

    for d in docs:
        mgr.upsert_document(COLLECTION, d)

    print("[Setup] Data upserted. Waiting for indexing...", flush=True)
    time.sleep(2)
    return mgr


def test_multitenancy_scenarios(manager):
    # Use unique query to avoid stale cache hits from previous runs
    query = f"information note secret {time.time()}"
    cfg = manager.pipeline_config.copy()
    cfg["use_reranker"] = False  # Simplify

    print("\n--- Test 1: Guest Access ---")
    results = run_query_pipeline(
        manager, query, top_k=10, collections=[COLLECTION], cfg=cfg, user_context=None
    )

    # Extract original IDs from payload
    found_ids = [r.get("payload", {}).get("id") for r in results]
    print(f"Guest found: {found_ids}")

    assert "doc_public" in found_ids
    assert "doc_user_a" not in found_ids
    assert "doc_user_b" not in found_ids
    assert "doc_admin" not in found_ids
    print("[OK] Guest Test Passed")

    print("\n--- Test 2: User A Access ---")
    ctx_a = {"user_id": "user_a", "role": "user"}
    results = run_query_pipeline(
        manager, query, top_k=10, collections=[COLLECTION], cfg=cfg, user_context=ctx_a
    )
    found_ids = [r.get("payload", {}).get("id") for r in results]
    print(f"User A found: {found_ids}")
    assert "doc_public" in found_ids
    assert "doc_user_a" in found_ids
    assert "doc_user_b" not in found_ids
    assert "doc_admin" not in found_ids
    print("[OK] User A Test Passed")

    print("\n--- Test 3: Admin Access ---")
    ctx_admin = {"user_id": "admin_user", "role": "admin"}
    results = run_query_pipeline(
        manager,
        query,
        top_k=10,
        collections=[COLLECTION],
        cfg=cfg,
        user_context=ctx_admin,
    )
    found_ids = [r.get("payload", {}).get("id") for r in results]
    print(f"Admin found: {found_ids}")
    print(f"Admin found: {found_ids}")
    assert "doc_public" in found_ids
    assert "doc_user_a" not in found_ids  # Admin restricted to public
    assert "doc_user_b" not in found_ids  # Admin restricted to public
    assert (
        "doc_admin" in found_ids
    )  # Admin doc is public tenant? No, doc_admin tenant="public". Correct.
    print("[OK] Admin Test Passed")

    print("\n--- Test 4: Semantic Cache Isolation ---")
    # 1. User A searches
    print("User A searching 'cache_test'...")
    run_query_pipeline(
        manager,
        "cache_test",
        top_k=5,
        collections=[COLLECTION],
        cfg=cfg,
        user_context=ctx_a,
    )

    # 2. User B searches same query -> Should NOT allow seeing User A's cached doc if it was there (doc_user_a)
    # But note: "cache_test" might not match doc_user_a semantically well.
    # Let's search for "User A" which matches doc_user_a strongly.

    print("User A searching 'User A'...")
    res_a = run_query_pipeline(
        manager,
        "User A",
        top_k=5,
        collections=[COLLECTION],
        cfg=cfg,
        user_context=ctx_a,
    )
    found_ids_a = [r.get("payload", {}).get("id") for r in res_a]
    assert "doc_user_a" in found_ids_a

    print(
        "User B searching 'User A' (Should yield public docs only, NOT User A's doc from cache)"
    )
    ctx_b = {"user_id": "user_b", "role": "user"}
    res_b = run_query_pipeline(
        manager,
        "User A",
        top_k=5,
        collections=[COLLECTION],
        cfg=cfg,
        user_context=ctx_b,
    )
    found_ids_b = [r.get("payload", {}).get("id") for r in res_b]
    print(f"User B found: {found_ids_b}")

    assert "doc_user_a" not in found_ids_b
    print("[OK] Cache Isolation Passed")
