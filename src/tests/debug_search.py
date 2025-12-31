import sys
import os
import asyncio

# Ensure src is in path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager

async def main():
    with acquire_manager() as mgr:
        query = "인공지능 연구"
        print(f"Querying for '{query}' in 'csweb.ai'...")
        
        # Test 1: Explicit collection
        results = mgr.query(query, top_k=5, collections=["csweb.ai"])
        print(f"\n[Explicit] Found {len(results)} results:")
        for r in results:
            # Handle both dict and object
            score = r.score if hasattr(r, 'score') else r.get('score', 0)
            payload = r.payload if hasattr(r, 'payload') else r.get('payload', {})
            title = payload.get('title', 'No Title')
            print(f" - {score:.4f} | {title}")

        # Test 2: Auto collection (if default is wrong)
        print(f"\n[Auto] Querying (default collection: {mgr.default_collection})...")
        results = mgr.query(query, top_k=5)
        print(f"Found {len(results)} results.")

if __name__ == "__main__":
    asyncio.run(main())
