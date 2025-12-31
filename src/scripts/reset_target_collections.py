import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager

TARGET_COLS = ["csweb.news", "csweb.research"]

async def reset_collections():
    print(f"🗑️ Deleting collections: {TARGET_COLS}")
    
    with acquire_manager() as mgr:
        for col in TARGET_COLS:
            try:
                mgr.client.delete_collection(col)
                print(f"✅ Deleted {col}")
            except Exception as e:
                print(f"⚠️ Failed to delete {col} (maybe not exist): {e}")

if __name__ == "__main__":
    asyncio.run(reset_collections())
