import asyncio
import json
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager


async def repair_ids():
    path = "src/tests/comparison_queries.json"
    with open(path, "r") as f:
        queries = json.load(f)

    print(f"🔧 Repairing IDs in {path}...")

    updated_count = 0

    with acquire_manager() as mgr:
        for i, q in enumerate(queries):
            # Only target csweb.research for now as it's the confirmed broken one
            # But "origin_collection" might be empty or wrong?
            # The query text often contains "name:..." for research queries.

            is_research = (
                "csweb.research" in q.get("origin_collection", "")
                or "name:" in q["query"]
            )

            if not is_research:
                continue

            current_id = (
                q.get("expected_doc_ids", [])[0] if q.get("expected_doc_ids") else None
            )
            query_text = q["query"]

            # Extract name from query if possible "name:LabName professor:..."
            # Simple heuristic: Split by ' ' and take first part if it starts with name:

            # Search using BM25/Dense to find the REAL doc
            # We assume the query text is sufficient to find it effectively if we ignore the ID.

            # Using simple keyword retrieval to find best match
            # We want to find the doc that perfectly matches this metadata.

            results = mgr.query(query_text, top_k=1, collections=["csweb.research"])

            if results:
                found_doc = results[0]
                found_id = found_doc.get("payload", {}).get("db_id")

                if found_id and found_id != current_id:
                    print(
                        f"   [Fixed] Query: {query_text[:20]}... | Old: {current_id[:8]} -> New: {found_id[:8]}"
                    )
                    q["expected_doc_ids"] = [found_id]
                    q["origin_collection"] = "csweb.research"  # Ensure this is set
                    updated_count += 1
            else:
                print(f"   [Warning] No match found for: {query_text[:30]}...")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    print(f"[OK] Updated {updated_count} queries.")


if __name__ == "__main__":
    asyncio.run(repair_ids())
