"""
벤치마크 실행 스크립트
"""

import asyncio
import argparse
import sys
import os

# Ensure src is in path (priority)
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from tests.benchmark import PerformanceBenchmark
from llm_backend.server.vector_server.core.resource_pool import acquire_manager


class DBAdapter:
    """Adapts VectorDBManager to the interface expected by PerformanceBenchmark"""

    def __init__(self, mgr):
        self.mgr = mgr

    async def search(self, query: str, top_k: int = 10):
        # Bridge to sync method mgr.query with all collections
        collections = []
        try:
            resp = self.mgr.client.get_collections()
            collections = [c.name for c in resp.collections]
        except Exception:
            collections = [self.mgr.default_collection]

        return await asyncio.to_thread(
            self.mgr.query, query, top_k=top_k, collections=collections
        )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", required=True, help="Experiment phase name (e.g. baseline)"
    )
    parser.add_argument(
        "--queries", default="src/tests/test_queries.json", help="Path to test queries"
    )
    parser.add_argument(
        "--num_queries", type=int, default=20, help="Number of queries to run"
    )
    args = parser.parse_args()

    print(f"Initializing Benchmark Runner for phase: {args.phase}")

    benchmark = PerformanceBenchmark(test_queries_path=args.queries)
    if not benchmark.test_queries:
        print("[FAIL] No test queries loaded. Please run generate_test_data.py first.")
        return

    # Limit queries for baseline speed
    if len(benchmark.test_queries) > args.num_queries:
        benchmark.test_queries = benchmark.test_queries[: args.num_queries]

    with acquire_manager() as mgr:
        print("[OK] VectorDB Manager acquired.")
        adapter = DBAdapter(mgr)

        # Run full benchmark
        await benchmark.run_full_benchmark(adapter, args.phase)

        # Optional: Compare with baseline if this is not baseline
        if args.phase != "baseline":
            try:
                benchmark.compare_phases("baseline", args.phase)
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
