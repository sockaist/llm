import asyncio
import os
import sys

# Priority for local 'src'
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager


async def test_temporal_search():
    print("=== Testing Temporal Search ===")

    queries = [
        "딥러닝 기술",  # Normal query
        "최신 딥러닝 기술",  # Soft Recency intent
        "2024년 딥러닝 기술",  # Hard Filter: 2024
        "2021년 소식",  # Hard Filter: 2021
    ]

    with acquire_manager() as mgr:
        for q in queries:
            print(f"\nQuery: '{q}'")
            # Normal search with temporal detection
            results = mgr.query(q, top_k=5, collections=["csweb.ai"])

            for i, r in enumerate(results):
                date = r.get("payload", {}).get("date", "N/A")
                score = r.get("score", 0.0)
                rec_score = r.get("recency_score", "N/A")
                title = r.get("title", "")[:40]
                print(
                    f"{i + 1}. [{date}] Score: {score:.4f} (Rec: {rec_score}) | {title}"
                )


if __name__ == "__main__":
    asyncio.run(test_temporal_search())
