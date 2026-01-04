import asyncio
import json
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager


async def verify_ids():
    with open("src/tests/comparison_queries.json", "r") as f:
        queries = json.load(f)

    # Filter for research queries
    research_queries = [
        q for q in queries if "csweb.research" in q.get("origin_collection", "")
    ]

    print(f"🕵️ Verifying IDs for {len(research_queries)} research queries...")

    with acquire_manager() as mgr:
        # Get all IDs in collection
        try:
            # Fetch all points (limit 100 for safety, but we know there are only 46)
            hits, _ = mgr.client.scroll(
                collection_name="csweb.research", limit=100, with_payload=True
            )
            all_db_ids = {h.payload.get("db_id") for h in hits}
            print(f"📚 Collection contains {len(all_db_ids)} unique db_ids.")

            missing_count = 0
            for q in research_queries:
                expected = q.get("expected_doc_ids", [])
                if not expected:
                    continue
                target = expected[0]

                if target not in all_db_ids:
                    print(f"[FAIL] Missing ID: {target} (Query: {q['query'][:30]}...)")
                    missing_count += 1

            print(
                f"\n📉 Result: {missing_count}/{len(research_queries)} queries have MISSING target docs."
            )

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(verify_ids())
