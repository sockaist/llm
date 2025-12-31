import asyncio
import json
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager

async def diagnose_failures():
    # Load test queries
    with open("src/tests/comparison_queries.json", "r") as f:
        queries = json.load(f)
    
    # Filter for research queries only
    research_queries = [q for q in queries if "csweb.research" in q.get("origin_collection", "")]
    if not research_queries:
         research_queries = queries[:5]

    print(f"🔍 Diagnosing {len(research_queries)} research queries...")
    
    dense_hits = 0
    dense_rrs = 0.0
    sparse_hits = 0
    sparse_rrs = 0.0
    splade_hits = 0
    splade_rrs = 0.0
    
    with acquire_manager() as mgr:
        for q in research_queries:
            query_text = q["query"]
            expected_ids = q.get("expected_doc_ids", [])
            q.get("query_type", "unknown")
            
            if not expected_ids: 
                continue
            
            target_id = str(expected_ids[0])
            print(f"\nEvaluating: '{query_text}' -> Target: {target_id[:8]}...")
            
            # 1. Search Dense
            dense_res, _, _ = mgr._search_collection_unique(
                "csweb.research", query_text, top_k=50, 
                use_dense=True, use_sparse=False, use_splade=False
            )
            
            # Check ID match
            dense_rank = None
            for i, r in enumerate(dense_res):
                # Check point UUID, payload id, payload db_id
                rid = str(r.id)
                pid = str(r.payload.get('id', ''))
                dbid = str(r.payload.get('db_id', ''))
                
                if target_id in [rid, pid, dbid]:
                    dense_rank = i
                    break
            
            if dense_res:
                top1_dbid = dense_res[0].payload.get('db_id', 'unknown')
                print(f"   [Dense] Top result: {top1_dbid[:8]}... (Score: {dense_res[0].score:.4f})")

            # 2. Search Sparse (BM25)
            _, sparse_res, _ = mgr._search_collection_unique(
                "csweb.research", query_text, top_k=50, 
                use_dense=False, use_sparse=True, use_splade=False
            )
            sparse_rank = None
            for i, r in enumerate(sparse_res):
                rid = str(r.id)
                pid = str(r.payload.get('id', ''))
                dbid = str(r.payload.get('db_id', ''))
                if target_id in [rid, pid, dbid]:
                    sparse_rank = i
                    break
            
            if sparse_res:
                top1_dbid = sparse_res[0].payload.get('db_id', 'unknown')
                print(f"   [BM25]  Top result: {top1_dbid[:8]}... (Score: {sparse_res[0].score:.4f})")

            # 3. Search SPLADE
            _, _, splade_res = mgr._search_collection_unique(
                "csweb.research", query_text, top_k=50, 
                use_dense=False, use_sparse=False, use_splade=True
            )
            splade_rank = None
            for i, r in enumerate(splade_res):
                rid = str(r.id)
                pid = str(r.payload.get('id', ''))
                dbid = str(r.payload.get('db_id', ''))
                if target_id in [rid, pid, dbid]:
                    splade_rank = i
                    break

            if splade_res:
                top1_dbid = splade_res[0].payload.get('db_id', 'unknown')
                print(f"   [SPLADE] Top result: {top1_dbid[:8]}... (Score: {splade_res[0].score:.4f})")

            print(f"   => Ranks: Dense={dense_rank}, BM25={sparse_rank}, SPLADE={splade_rank}")
            
            if dense_rank is not None:
                dense_hits += 1
                dense_rrs += 1.0 / (dense_rank + 1)
            
            if sparse_rank is not None:
                sparse_hits += 1
                sparse_rrs += 1.0 / (sparse_rank + 1)
                
            if splade_rank is not None:
                splade_hits += 1
                splade_rrs += 1.0 / (splade_rank + 1)

    total = len(research_queries)
    print(f"\n📊 Diagnosis Summary (N={total})")
    print(f"   - Dense : Hit Rate={dense_hits/total*100:.1f}% | MRR={dense_rrs/total:.3f}")
    print(f"   - BM25  : Hit Rate={sparse_hits/total*100:.1f}% | MRR={sparse_rrs/total:.3f}")
    print(f"   - SPLADE: Hit Rate={splade_hits/total*100:.1f}% | MRR={splade_rrs/total:.3f}")

if __name__ == "__main__":
    asyncio.run(diagnose_failures())
