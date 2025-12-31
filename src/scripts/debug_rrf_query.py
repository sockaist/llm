import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager

async def debug_query():
    # A query that should have results
    query_text = "KAIST CCC(Computing Convergence Consortium) 회원사가?"
    target_col = "csweb.news"
    
    print(f"🔎 Debugging Query: {query_text}")
    
    with acquire_manager() as mgr:
        # Force config
        mgr.pipeline_config["use_bandit"] = False
        mgr.pipeline_config["use_rrf"] = True
        mgr.pipeline_config["use_sparse"] = True
        mgr.pipeline_config["use_splade"] = True
        mgr.pipeline_config["search_k"] = 100
        mgr.pipeline_config["dense_weight"] = 1.0
        mgr.pipeline_config["sparse_weight"] = 1.0
        mgr.pipeline_config["splade_weight"] = 1.0
        
        # Call query
        # Since we modified search_pipeline.py to log [RRF Debug], we should see it.
        # But we also want to inspect return value here.
        
        res = mgr.query(query_text, top_k=10, collections=[target_col])
        
        print(f"\n✅ Result Count: {len(res)}")
        for i, r in enumerate(res):
            print(f"   [{i}] {r.get('title')} (Score: {r.get('score'):.4f})")
            # Trace debug might show why sparse was 0 if it was

if __name__ == "__main__":
    asyncio.run(debug_query())
