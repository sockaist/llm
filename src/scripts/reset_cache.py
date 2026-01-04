import sys
import os
import asyncio

# Ensure src is in path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.core.semantic_cache import SemanticCache
from llm_backend.vectorstore.config import VECTOR_SIZE


async def reset_cache():
    print(f"🔄 Resetting Semantic Cache (Target Dim: {VECTOR_SIZE})...")

    with acquire_manager() as mgr:
        client = mgr.client
        col_name = SemanticCache.COLLECTION_NAME

        # 1. Check existing
        if client.collection_exists(col_name):
            try:
                info = client.get_collection(col_name)
                print(f"   Found existing cache (Status: {info.status})")
                client.delete_collection(col_name)
                print(f"[OK] Deleted old collection: {col_name}")
            except Exception as e:
                print(f"[WARN] Error deleting collection: {e}")

        # 2. Re-create via init_cache
        SemanticCache.init_cache(client, vector_size=VECTOR_SIZE)

        # 3. Verify
        try:
            info = client.get_collection(col_name)
            print(f"[OK] Created new cache: {col_name}")
            print(f"   Vector Config: {info.config.params.vectors}")
        except Exception as e:
            print(f"[FAIL] Verification failed: {e}")


if __name__ == "__main__":
    asyncio.run(reset_cache())
