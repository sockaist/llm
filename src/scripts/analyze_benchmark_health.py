import asyncio
import json
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager


async def analyze_health():
    path = "src/tests/comparison_queries.json"
    with open(path, "r") as f:
        queries = json.load(f)

    research_queries = [
        q
        for q in queries
        if "csweb.research" in q.get("origin_collection", "") or "name:" in q["query"]
    ]

    print(f"📊 Analyzing {len(research_queries)} research queries...")

    with acquire_manager() as mgr:
        hits, _ = mgr.client.scroll(
            collection_name="csweb.research", limit=100, with_payload=True
        )
        valid_ids = {h.payload.get("db_id") for h in hits}

        valid_count = 0
        invalid_count = 0

        for q in research_queries:
            target = (
                q.get("expected_doc_ids", [])[0] if q.get("expected_doc_ids") else None
            )

            if target in valid_ids:
                valid_count += 1
            else:
                invalid_count += 1
                # print(f"   [Invalid] {q['query'][:40]}... -> {target}")

        print(f"   - Valid Targets: {valid_count}")
        print(f"   - Invalid Targets: {invalid_count}")
        print(f"   - Coverage: {valid_count / len(research_queries) * 100:.1f}%")


if __name__ == "__main__":
    asyncio.run(analyze_health())
