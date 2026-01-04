import asyncio
import os
import sys
import json
import time
import numpy as np

# Setup Path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager


def calculate_ndcg(retrieved_ids, relevant_ids, k=5):
    dcg = 0.0
    idcg = 0.0
    rel_set = set(relevant_ids)

    # DCG
    for i in range(min(len(retrieved_ids), k)):
        doc_id = retrieved_ids[i]
        if doc_id in rel_set:
            dcg += 1.0 / np.log2(i + 2)

    # IDCG (Ideal: all relevant docs at top)
    # matching the number of relevant docs available, up to k
    num_rel = min(len(rel_set), k)
    for i in range(num_rel):
        idcg += 1.0 / np.log2(i + 2)

    return dcg / idcg if idcg > 0 else 0.0


async def run_bench(output_file="benchmark_results.json"):
    print(f"🏃 Running Comparative Benchmark -> {output_file}")

    with open("src/tests/comparison_queries.json", "r") as f:
        queries = json.load(f)

    results = {"metrics": {}, "details": []}

    total_queries = len(queries)
    hits_1 = 0
    hits_5 = 0
    hits_10 = 0
    mrr_sum = 0
    ndcg_sum = 0

    with acquire_manager() as mgr:
        # Get all collections for global search context
        # Or just target specifically? User said "csweb.news, csweb.research".
        # But real world usage is global. Let's stick to global to be fair to "Before/After" consistency.
        # But wait, if other collections exist with old embeddings (768), and I switch to 1024,
        # global search will fail/crash on dimension mismatch!
        # CRITICAL: When I switch models, I MUST ONLY search collections that match the new dimension.
        # Implication: I must delete/ignore old collections or only search specific ones.
        # Decision: I will explicitly search ONLY `csweb.news` and `csweb.research` for this benchmark.
        target_cols = ["csweb.news", "csweb.research"]
        print(f"Targets: {target_cols}")

        # FORCE CONFIG Optimization for RRF
        mgr.pipeline_config["use_bandit"] = False
        mgr.pipeline_config["use_rrf"] = True
        mgr.pipeline_config["rrf_k"] = 60
        # Set explicitly static weights (though RRF handles them, we want to ensure candidates are fetched)
        # Note: 'hp_tuner' logic falls back to these if bandit is off
        mgr.pipeline_config["dense_weight"] = 1.0
        mgr.pipeline_config["sparse_weight"] = 1.0
        mgr.pipeline_config["splade_weight"] = 1.0
        mgr.pipeline_config["title_weight"] = 0.5
        mgr.pipeline_config["search_k"] = 100  # Fetch more for RRF ranking

        print("🔧 Config Overrides: RRF=True, Bandit=False, Search_K=100")

        for i, q in enumerate(queries):
            query_text = q["query"]
            expected_ids = set(q["expected_doc_ids"])  # list

            # Run Query
            start_t = time.perf_counter()
            try:
                # We assume mgr.query handles search across these cols
                res = mgr.query(query_text, top_k=10, collections=target_cols)
            except Exception as e:
                print(f"Query failed: {e}")
                res = []

            latency = (time.perf_counter() - start_t) * 1000

            # Analyze
            hit_rank = 0
            found_ids = []

            for rank, r in enumerate(res):
                rid = r.get("id")
                pid = r.get("db_id")  # normalized
                found_ids.append(pid or rid)

                if (rid in expected_ids or pid in expected_ids) and hit_rank == 0:
                    hit_rank = rank + 1

            # Metrics
            is_hit_1 = 1 if hit_rank == 1 else 0
            is_hit_5 = 1 if 0 < hit_rank <= 5 else 0
            is_hit_10 = 1 if 0 < hit_rank <= 10 else 0

            hits_1 += is_hit_1
            hits_5 += is_hit_5
            hits_10 += is_hit_10

            mrr = 1.0 / hit_rank if hit_rank > 0 else 0.0
            mrr_sum += mrr

            ndcg = calculate_ndcg(found_ids, expected_ids, k=5)
            ndcg_sum += ndcg

            results["details"].append(
                {
                    "query": query_text,
                    "hit_rank": hit_rank,
                    "ndcg": ndcg,
                    "latency": latency,
                }
            )

            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{total_queries}...")

    # Aggregates
    metrics = {
        "hit@1": hits_1 / total_queries,
        "hit@5": hits_5 / total_queries,
        "hit@10": hits_10 / total_queries,
        "mrr": mrr_sum / total_queries,
        "ndcg@5": ndcg_sum / total_queries,
    }

    results["metrics"] = metrics

    print("\n" + "=" * 40)
    print(f"📊 Results: {output_file}")
    print(f"Hit@1:  {metrics['hit@1']:.1%}")
    print(f"Hit@5:  {metrics['hit@5']:.1%}")
    print(f"Hit@10: {metrics['hit@10']:.1%}")
    print(f"MRR:    {metrics['mrr']:.3f}")
    print(f"NDCG@5: {metrics['ndcg@5']:.3f}")
    print("=" * 40)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        out = sys.argv[1]
    else:
        out = "benchmark_baseline_results.json"
    asyncio.run(run_bench(out))
