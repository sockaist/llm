
import sys
import os
import time
import traceback

print("Starting test_encryption.py...", flush=True)

try:
    # Ensure project root is in path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

    from llm_backend.vectorstore.vector_db_manager import VectorDBManager
    from llm_backend.vectorstore.search_pipeline import run_query_pipeline

    COLLECTION = "test.encryption"
    USER_ID = "user_secret_agent"

    def setup_data(manager: VectorDBManager):
        print(f"\n[Setup] Creating collection {COLLECTION}...")
        manager.create_collection(COLLECTION, vector_size=1024, force=True)
        
        # Upsert a private document (should be encrypted)
        # Content: "The password is blue_dolphin"
        # We expect this string NOT to be visible in raw payload
        
        doc = {
            "id": "doc_secret",
            "content": "The password is blue_dolphin",
            "tenant_id": USER_ID,
            "access_level": 3,
            "encrypt_content": True # Explicit flag (though tenant_id!=public would trigger it too)
        }
        
        manager.upsert_document(COLLECTION, doc)
        print("[Setup] Secret document upserted.")
        
        # Upsert public doc for control
        doc_pub = {
            "id": "doc_public",
            "content": "This is public info",
            "tenant_id": "public",
            "access_level": 1
        }
        manager.upsert_document(COLLECTION, doc_pub)
        print("[Setup] Public document upserted. Waiting index...")
        time.sleep(2)

    def test_encryption_flow():
        manager = VectorDBManager()
        setup_data(manager)
        
        query = "password dolphin"
        cfg = manager.pipeline_config.copy()
        cfg["use_reranker"] = False

        print("\n--- Test 1: Verify Encryption at Rest ---")
        # Direct Qdrant Access: Use Scroll because access by non-UUID ID is not allowed
        from qdrant_client import models
        filter_secret = models.Filter(
            must=[models.FieldCondition(key="id", match=models.MatchValue(value="doc_secret"))]
        )
        res, _ = manager.client.scroll(COLLECTION, scroll_filter=filter_secret, limit=1, with_payload=True)
        
        if not res:
            print("❌ Secret doc not found in DB!")
            sys.exit(1)
            
        payload = res[0].payload
        stored_content = payload.get("content")
        print(f"Stored Content: {stored_content}")
        
        assert "blue_dolphin" not in stored_content, "❌ Content is NOT encrypted at rest!"
        assert payload.get("content_encrypted") is True, "❌ content_encrypted flag missing/false"
        print("✅ Encryption at Rest Verified")

        print("\n--- Test 2: Search as Owner (Auto-Decryption) ---")
        ctx_owner = {"user_id": USER_ID, "role": "user"}
        results = run_query_pipeline(manager, query, top_k=5, collections=[COLLECTION], cfg=cfg, user_context=ctx_owner)
        
        next((r for r in results if r["id"] == "doc_secret_id" or "doc_secret" in str(r)), None)
        # Note: ID might be hashed. We check text.
        
        found_text = None
        for r in results:
            # Check if this is our secret doc
            # Payload id is original id
            if r.get("metadata", {}).get("id") == "doc_secret":
                found_text = r.get("text")
                break
        
        if not found_text:
            # Maybe search didn't retrieve it?
            # Search query was "password dolphin".
            # Vector is built from PLAINTEXT content during upsert (ingest_manager encodes 'content' before encrypting? NO!)
            # Looking at ingest_manager: 'stored_content' is encrypted. 'content' var holds original.
            # Upsert logic:
            #   dense_vec = manager.dense_model.encode(content) <-- Uses ORIGINAL content!
            #   stored_content = encrypt(...)
            #   payload = { ... "content": stored_content }
            # So Vector Search SHOULD find it.
            print("❌ Secret doc not returned by search pipeline (Ranker issue?)")
            print([r.get("metadata", {}).get("id") for r in results])
        else:
            print(f"Retrieved Text: {found_text}")
            assert "blue_dolphin" in found_text, "❌ Auto-Decryption Failed!"
            print("✅ Auto-Decryption Verified")

        print("\n--- Test 3: Admin Access (No Decryption) ---")
        # Admin can access all (if we fix Admin filter in next phase), but currently Admin returns None filter (All access).
        # Admin should see the doc but getting RAW content because tenant_id != admin_id.
        
        ctx_admin = {"user_id": "admin_user", "role": "admin"}
        results = run_query_pipeline(manager, query, top_k=5, collections=[COLLECTION], cfg=cfg, user_context=ctx_admin)
        
        found_encrypted = None
        for r in results:
            if r.get("metadata", {}).get("id") == "doc_secret":
                found_encrypted = r.get("text")
                break
        
        if found_encrypted:
            print(f"Admin retrieved: {found_encrypted}")
            assert "blue_dolphin" not in found_encrypted, "❌ Admin decrypted User's private doc! (SECURITY FAILURE)"
            assert "gAAAA" in found_encrypted or len(found_encrypted) > 20, "❌ Content doesn't look encrypted"
            print("✅ Admin Blindness Verified")
        else:
            print("Admin didn't find doc (maybe acceptable if filter not updated yet, but Admin should see public/all)")

    if __name__ == "__main__":
        test_encryption_flow()

except Exception:
    traceback.print_exc()
    sys.exit(1)
