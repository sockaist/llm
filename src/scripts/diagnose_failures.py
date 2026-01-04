import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.metadata_router import MetadataRouter


async def diagnose():
    print("🩺 Starting Diagnosis: Zero-Result Queries")

    with open("src/tests/comparison_queries.json", "r") as f:
        queries = json.load(f)

    zero_count = 0
    filter_blame_count = 0
    total = len(queries)

    # Target collections used in benchmark
    target_cols = ["csweb.news", "csweb.research"]

    with acquire_manager() as mgr:
        # Force same config as benchmark (RRF=True, Bandit=False)
        mgr.pipeline_config["use_bandit"] = False
        mgr.pipeline_config["use_rrf"] = True
        mgr.pipeline_config["rrf_k"] = 60
        mgr.pipeline_config["search_k"] = 100
        mgr.pipeline_config["dense_weight"] = 1.0
        mgr.pipeline_config["sparse_weight"] = 1.0
        mgr.pipeline_config["splade_weight"] = 1.0
        mgr.pipeline_config["title_weight"] = 0.5

        print(f"📊 Analyzing {total} queries against {target_cols}...")

        failure_log = []

        for i, q in enumerate(queries):
            query_text = q["query"]

            # 1. Check Metadata Router extraction first
            filters = MetadataRouter.extract_filters(query_text)

            # 2. Run Query
            res = mgr.query(query_text, top_k=10, collections=target_cols)

            if not res:
                zero_count += 1
                reason = "Unknown"

                # Diagnosis Logic
                if filters:
                    reason = f"Filtered ({filters})"
                    filter_blame_count += 1

                    # Dry run without filters to see if it would have worked
                    # We can't easily bypass filter in mgr.query without hacking config or code
                    # But we can infer.
                else:
                    reason = "Low Score / No Match"

                print(
                    f"[FAIL] [Query {i}] 0 Results: '{query_text}' -> Reason: {reason}"
                )
                failure_log.append(
                    {
                        "query": query_text,
                        "reason": reason,
                        "filters": str(filters) if filters else None,
                    }
                )

    print("\n" + "=" * 40)
    print("📉 Diagnosis Result")
    print(f"Total Queries: {total}")
    print(f"Zero Results:  {zero_count} ({zero_count / total:.1%})")
    print(f"  - Due to Filters: {filter_blame_count}")
    print(f"  - Due to Retrieval: {zero_count - filter_blame_count}")
    print("=" * 40)

    # Save log
    with open("diagnosis_report.json", "w") as f:
        json.dump(failure_log, f, indent=2, ensure_ascii=False)
        print("📝 Detailed log saved to diagnosis_report.json")


if __name__ == "__main__":
    asyncio.run(diagnose())
