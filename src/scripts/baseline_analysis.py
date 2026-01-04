import time
import asyncio
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager


class Timer:
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        elapsed = (time.perf_counter() - self.start) * 1000
        print(f"{self.name}: {elapsed:.2f}ms")


async def profile_search_pipeline(mgr, query: str, col: str):
    print(f"\n--- Profiling Query: '{query}' ---")

    # 1. Total Pipeline Time (includes Cache, Encoder, Search, Rerank, Boost)
    with Timer("TOTAL PIPELINE"):
        results = mgr.query(query, top_k=5, collections=[col])

    # Identify if it was a cache hit
    # Note: mgr.query results are lists of dicts
    # We can't easily peek inside unless we add more logging or check the logs
    print(f"Results returned: {len(results)}")
    if results:
        print(
            f"Top result parent context: {'Yes' if results[0].get('parent_context') else 'No'}"
        )
        print(f"Boost applied: {'Yes' if results[0].get('_boost_reason') else 'No'}")


async def run_comprehensive_analysis():
    col = "benchmark.real.phase7"
    with acquire_manager() as mgr:
        # Warmup and clear caches for fresh measurements
        os.system(
            "PYTHONPATH=$PYTHONPATH:$(pwd)/src python src/scripts/clear_caches.py"
        )

        test_queries = [
            "전산학부 졸업 학점 요건",  # Technical, should be cached after first run
            "김정연 전산학부 졸업",  # Entity-heavy, should trigger routing & boost
            "전산과 졸업",  # Alias, should trigger normalization
            "What is computer science at KAIST?",  # English
        ]

        print("\n--- [ROUND 1] Fresh Search (No Cache) ---")
        for q in test_queries:
            await profile_search_pipeline(mgr, q, col)

        print("\n--- [ROUND 2] Cached Search (Semantic Cache) ---")
        # Reuse same queries to test cache hits
        for q in test_queries:
            await profile_search_pipeline(mgr, q, col)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_analysis())
