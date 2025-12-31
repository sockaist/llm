import asyncio
import os
import sys
import json
from collections import defaultdict

# Setup Path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager

async def run_diagnostic(query_limit=50):
    print(f"🕵️  Starting Diagnostic Analysis (Limit: {query_limit} queries)...")
    
    with open("src/tests/test_queries.json", 'r', encoding='utf-8') as f:
        queries = json.load(f)
    
    # Stratified sample if possible, or just first N
    test_queries = queries[:query_limit]
    
    metrics_by_col = defaultdict(lambda: {"count": 0, "hit": 0, "rr": 0.0})
    
    with acquire_manager() as mgr:
        # Get all collections
        resp = mgr.client.get_collections()
        all_cols = [c.name for c in resp.collections]
        
        print(f"Targeting {len(all_cols)} collections.")
        
        for i, q in enumerate(test_queries):
            query_text = q['query']
            expected_ids = set(q['expected_doc_ids'])
            q.get('query_type')
            origin = q.get('origin_collection')
            
            # 1. Run Search
            # We want to know WHY it failed or succeeded. 
            # Ideally we peek into the components, but mgr.query hides it.
            # We will approximate by running the query and checking the 'strategy' output if available,
            # or by deducing from results.
            
            # Since we can't easily decouple dense/sparse inside mgr.query without modifying code,
            # we will blindly trust the output for collection stats, 
            # and use a separate probing for method comparison if needed.
            
            # PROBING: Check "Dense-Only" and "Sparse-Only" capability?
            # It's hard without modifying the pipeline config. 
            # Let's just analyze the FINAL result for Collection Bias first.
            
            res = mgr.query(query_text, top_k=10, collections=all_cols)
            
            # Analyze Result
            hit = False
            rank = 0
            
            if res:
                # Top result collection
                res[0].get('collection', 'unknown')
                
                # Check Hit
                for idx, r in enumerate(res):
                    rid = r.get('id')
                    pid = r.get('payload', {}).get('db_id')
                    if rid in expected_ids or pid in expected_ids:
                        hit = True
                        rank = idx + 1
                        r.get('collection', 'unknown') # Attribute success to this collection
                        break
            
            # Update metrics
            target_col = origin if isinstance(origin, str) else "mixed"
            if isinstance(origin, list):
                target_col = "mixed"
            
            # We group by the EXPECTED collection (Origin) to see which collections are hard to query
            group_key = str(target_col)
            
            metrics_by_col[group_key]["count"] += 1
            if hit:
                metrics_by_col[group_key]["hit"] += 1
                metrics_by_col[group_key]["rr"] += 1.0 / rank
                
            if (i+1) % 10 == 0:
                print(f"Processed {i+1}...")

    print("\n" + "="*60)
    print(f"{'Collection (Origin)':<30} | {'Count':<5} | {'Hit@10':<6} | {'MRR':<6}")
    print("-" * 60)
    
    sorted_stats = sorted(metrics_by_col.items(), key=lambda x: x[0])
    
    for col, stats in sorted_stats:
        cnt = stats['count']
        hit_rate = (stats['hit'] / cnt) * 100 if cnt > 0 else 0
        mrr = stats['rr'] / cnt if cnt > 0 else 0
        print(f"{col:<30} | {cnt:<5} | {hit_rate:5.1f}% | {mrr:.3f}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
