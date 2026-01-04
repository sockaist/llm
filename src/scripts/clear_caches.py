from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.core.semantic_cache import SemanticCache
from llm_backend.core.cache_manager import redis_client

with acquire_manager() as mgr:
    try:
        mgr.client.delete_collection(SemanticCache.COLLECTION_NAME)
        print(
            f"[OK] Semantic Cache collection '{SemanticCache.COLLECTION_NAME}' deleted."
        )
    except Exception as e:
        print(f"[WARN] Semantic Cache deletion failed: {e}")

if redis_client:
    try:
        redis_client.flushdb()
        print("[OK] Redis L2 cache flushed.")
    except Exception as e:
        print(f"[WARN] Redis flush failed: {e}")
else:
    print("[WARN] Redis client not available.")
