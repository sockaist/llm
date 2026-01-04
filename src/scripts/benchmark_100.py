import psutil
import asyncio
import os
import sys
import time
import json
import numpy as np

# Ensure src is in path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager


def calculate_ndcg(results, k=5):
    """Calculate NDCG@K for the benchmark."""
    ndcg_scores = []
    for r in results:
        # Ideal: The correct doc is at rank 1 -> max relevance
        # We assume binary relevance: correct doc = 1, others = 0
        rank = r["rank"]
        if rank == 0 or rank > k:
            dcg = 0.0
        else:
            # DCG formula: rel / log2(rank + 1)
            # here rel=1 for the correct doc
            dcg = 1.0 / np.log2(rank + 1)

        # IDCG: Perfect ranking means correct doc is at rank 1
        idcg = 1.0 / np.log2(1 + 1)  # which is 1.0

        ndcg_scores.append(dcg / idcg)
    return np.mean(ndcg_scores)


def calculate_advanced_metrics(results):
    # Precision/Recall/F1 logic (Hit@1 vs others as FN/FP is tricky in ranking)
    # We treat "Hit within Top 10" as TP
    # But strictly:
    # Precision@K = (Relevant docs in Top K) / K
    # Recall@K = (Relevant docs in Top K) / (Total Relevant Docs)

    recalls = []

    for r in results:
        # For our single-target queries (mostly), Total Relevant = 1 (or len(expected_ids))
        # But for multi-hop, expected_ids > 1
        # 'recall' field in result is already (found / expected)
        recalls.append(r.get("recall", 0.0))

        # Precision: If we found N relevant docs in Top 10, Precision = N / 10
        # Actually expected_ids tell us how many are relevant.
        # But we need to know HOW MANY of the returned docs matched expected.
        # 'recall' = matched / expected
        # 'matched' = recall * expected
        r.get("recall", 0.0)
        # We don't have expected count here easily unless we modify result struct
        # Let's approximate: Precision@10 ~ matched / 10
        # But we don't store matched count directly.
        # However, we can infer for single-doc query: precision = 1/10 if hit, else 0

        # Let's stick to simple Hit based proxies for now or update run loop to store 'found_count'
        pass

    return {
        "ndcg_at_5": calculate_ndcg(results, k=5),
        "mean_recall": np.mean(recalls) if recalls else 0.0,
    }


def calculate_metrics(results):
    if not results:
        return {
            "count": 0,
            "hit_at_1": 0,
            "hit_at_5": 0,
            "mrr": 0,
            "avg_latency": 0,
            "p95_latency": 0,
            "avg_conf": 0,
            "avg_recall": 0,
            "ndcg_at_5": 0,
        }

    hits_at_1 = [r["rank"] == 1 for r in results]
    hits_at_5 = [r["rank"] > 0 and r["rank"] <= 5 for r in results]
    rr = [1.0 / r["rank"] if r["rank"] > 0 else 0.0 for r in results]
    latencies = [r["latency"] for r in results]
    confs = [r["confidence"] for r in results]
    recalls = [r.get("recall", 0.0) for r in results]

    ndcg = calculate_ndcg(results, k=5)

    return {
        "count": len(results),
        "hit_at_1": np.mean(hits_at_1),
        "hit_at_5": np.mean(hits_at_5),
        "mrr": np.mean(rr),
        "avg_latency": np.mean(latencies),
        "p95_latency": np.percentile(latencies, 95),
        "avg_conf": np.mean(confs),
        "avg_recall": np.mean(recalls),
        "ndcg_at_5": ndcg,
    }


def get_process_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB


async def run_benchmark_100(query_file="src/tests/test_queries.json"):
    print("[INFO] Starting 300-Query Benchmark with Advanced Metrics...")

    if not os.path.exists(query_file):
        print(f"[FAIL] Query file not found: {query_file}")
        return

    with open(query_file, "r", encoding="utf-8") as f:
        queries = json.load(f)

    print(f"Load {len(queries)} queries.")

    results = []
    errors = []
    col_stats = {}

    # Initial Resource Usage
    start_mem = get_process_memory()
    psutil.cpu_percent(interval=1)

    with acquire_manager() as mgr:
        # Pre-fetch all collections for global search
        all_cols_resp = mgr.client.get_collections()
        all_col_names = [c.name for c in all_cols_resp.collections]
        print(f"🌍 Global Search Scope: {len(all_col_names)} collections available.")

        # Warmup
        print("Warmup...")
        mgr.query("university", top_k=1)

        print("Running queries...")
        for i, q_item in enumerate(queries):
            query_text = q_item["query"]
            expected_ids = q_item["expected_doc_ids"]
            q_type = q_item.get("query_type", "unknown")
            origin_info = q_item.get("origin_collection")

            start = time.time()

            # Determine target collections
            target_cols = None
            if isinstance(origin_info, list) or q_type == "multi_hop":
                target_cols = all_col_names
            elif origin_info:
                target_cols = all_col_names

            try:
                res = mgr.query(query_text, top_k=10, collections=target_cols)
                error_msg = None
            except Exception as e:
                res = []
                error_msg = str(e)
                errors.append(
                    {"query": query_text, "error": error_msg, "col": str(origin_info)}
                )

            latency = (time.time() - start) * 1000

            # Check Metrics
            rank = 0
            top_score = 0.0
            recall = 0.0
            precision = 0.0  # Precision@10

            if res:
                top_score = (
                    res[0].get("confidence")
                    if res[0].get("confidence") is not None
                    else res[0].get("score", 0.0)
                )

                # Collection Usage Tracking
                top_col = res[0].get("collection", "unknown")
                col_stats[top_col] = col_stats.get(top_col, 0) + 1

                # 1. Rank
                for r_idx, r in enumerate(res):
                    rid = r.get("id")
                    pid = r.get("payload", {}).get("db_id") or r.get("payload", {}).get(
                        "id"
                    )
                    if rid in expected_ids or pid in expected_ids:
                        rank = r_idx + 1
                        break

                # 2. Recall & Precision
                retrieved_ids = set()
                for r in res:
                    retrieved_ids.add(r.get("id"))
                    retrieved_ids.add(r.get("payload", {}).get("db_id"))

                points_found = 0
                for eid in expected_ids:
                    if eid in retrieved_ids:
                        points_found += 1

                recall = points_found / len(expected_ids) if expected_ids else 0.0
                precision = points_found / len(res) if res else 0.0

            results.append(
                {
                    "query": query_text,
                    "type": q_type,
                    "rank": rank,
                    "latency": latency,
                    "confidence": top_score,
                    "recall": recall,
                    "precision": precision,
                    "error": error_msg,
                }
            )

            if (i + 1) % 50 == 0:
                mem = get_process_memory()
                print(f"Processed {i + 1}/{len(queries)}... Mem: {mem:.1f}MB")

    # Final Resource Usage
    end_mem = get_process_memory()
    end_cpu = psutil.cpu_percent(interval=None)  # Average since last call

    # Aggregation
    total_metrics = calculate_metrics(results)
    avg_precision = np.mean([r["precision"] for r in results])
    f1_score = (
        2
        * (avg_precision * total_metrics["avg_recall"])
        / (avg_precision + total_metrics["avg_recall"])
        if (avg_precision + total_metrics["avg_recall"]) > 0
        else 0.0
    )

    # Report Errors
    if errors:
        print("\n[WARN] ERRORS FOUND:")
        for e in errors[:5]:  # Show top 5
            print(f" - [{e['col']}] Query: '{e['query'][:20]}...' -> {e['error']}")
        print(f"Total Errors: {len(errors)}")

    print("\n" + "=" * 50)
    print("📊 BENCHMARK REPORT (Advanced Metrics)")
    print("=" * 50)
    print(f"Total Queries: {total_metrics['count']}")

    print(f"[OK] Hit@1:    {total_metrics['hit_at_1'] * 100:.1f}%")
    print(f"[OK] Hit@5:    {total_metrics['hit_at_5'] * 100:.1f}%")
    print(f"📈 MRR:      {total_metrics['mrr']:.3f}")
    print(f"⭐ NDCG@5:   {total_metrics['ndcg_at_5']:.3f} (New!)")

    print("-" * 30)
    print(f"🎯 Precision: {avg_precision:.3f} (@10)")
    print(f"[SEARCH] Recall:    {total_metrics['avg_recall']:.3f} (@10)")
    print(f"⚖️ F1 Score:  {f1_score:.3f}")
    print("-" * 30)

    total_time = sum([r["latency"] for r in results]) / 1000.0  # seconds
    qps = total_metrics["count"] / total_time if total_time > 0 else 0.0

    print(f"[ASYNC] Latency:   {total_metrics['avg_latency']:.1f}ms (Avg)")
    print(f"[INFO] QPS:       {qps:.1f} queries/sec")
    print(f"🛡️ Confid.:   {total_metrics['avg_conf']:.3f} (Avg)")
    print(f"💾 Memory:    {start_mem:.1f}MB -> {end_mem:.1f}MB")
    print(f"💻 CPU:       {end_cpu:.1f}%")

    print("-" * 50)
    print("📚 COLLECTION USAGE (Top-1 Result Source)")
    sorted_cols = sorted(col_stats.items(), key=lambda x: x[1], reverse=True)
    for cname, count in sorted_cols[:5]:  # Top 5
        print(f" - {cname:<20}: {count} queries")

    print("-" * 50)
    print("TYPE BREAKDOWN")
    print(f"{'Type':<10} | {'Count':<5} | {'NDCG':<5} | {'F1':<5} | {'Lat.':<6}")
    print("-" * 50)

    # By Type
    type_results = {}
    for r in results:
        t = r["type"]
        if t not in type_results:
            type_results[t] = []
        type_results[t].append(r)

    for t, rows in type_results.items():
        m = calculate_metrics(rows)
        ap = np.mean([x["precision"] for x in rows])
        f1 = (
            2 * (ap * m["avg_recall"]) / (ap + m["avg_recall"])
            if (ap + m["avg_recall"]) > 0
            else 0.0
        )
        print(
            f"{t:<10} | {m['count']:<5} | {m['ndcg_at_5']:.3f} | {f1:.3f} | {m['avg_latency']:4.0f}ms"
        )
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_benchmark_100())
