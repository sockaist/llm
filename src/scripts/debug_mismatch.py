import asyncio
import os
import sys
import json
from llm_backend.server.vector_server.core.resource_pool import acquire_manager

# Setup Path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))


async def debug_mismatch():
    print("🕵️  Debugging Embedding Mismatch...")
    query = "Vector Database"  # Generic query likely to be in benchmark
    # Use a query from the test set for better accuracy
    with open("src/tests/test_queries.json", "r") as f:
        qs = json.load(f)
        # Find a query for benchmark.real.phase7
        target_q = next(
            (q for q in qs if q.get("origin_collection") == "benchmark.real.phase7"),
            None,
        )
        if target_q:
            query = target_q["query"]
            print(f"Using query: {query}")
        else:
            print("No query found for benchmark.real.phase7, using generic.")

    col = "benchmark.real.phase7"

    with acquire_manager() as mgr:
        # 1. Dense Search
        print(f"\n--- DENSE SEARCH ({col}) ---")
        vec = mgr.dense_model.encode(query)
        d_res = mgr.client.query_points(
            collection_name=col, query=vec, using="dense", limit=10, with_payload=True
        ).points

        scores = [r.score for r in d_res]
        print(f"Dense Scores: {scores}")
        if scores:
            d_min, d_max = min(scores), max(scores)
            print(f"Spread: {d_max - d_min:.4f}")
            if d_max - d_min > 0:
                norm = [(s - d_min) / (d_max - d_min) for s in scores]
                print(f"Normalized: {[round(n, 2) for n in norm]}")

        for r in d_res[:3]:
            print(
                f"Score: {r.score:.4f} | ID: {r.id} | Text: {str(r.payload.get('text'))[:50]}..."
            )

        # 2. Sparse Search (if possible via client directly? client.search uses dense mostly unless names vector)
        # Qdrant client Python might need specific sparse syntax or use vector_db_helper
        from llm_backend.vectorstore.sparse_helper import bm25_encode
        from qdrant_client.models import SparseVector

        print(f"\n--- SPARSE SEARCH ({col}) ---")
        b_vec = bm25_encode(query)
        s_vec = SparseVector(indices=list(b_vec.keys()), values=list(b_vec.values()))

        # We assume 'sparse' is the vector name
        try:
            s_res = mgr.client.query_points(
                collection_name=col,
                query=s_vec,
                using="sparse",
                limit=5,
                with_payload=True,
            ).points

            for r in s_res:
                print(
                    f"Score: {r.score:.4f} | ID: {r.id} | Text: {str(r.payload.get('text'))[:50]}..."
                )
        except Exception as e:
            print(f"Sparse search failed: {e}")


if __name__ == "__main__":
    asyncio.run(debug_mismatch())
