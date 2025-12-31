import asyncio
import json
import os
import sys
import random

# Ensure src is in path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager

TARGET_COUNT = 300

async def generate_benchmark():
    print(f"🚀 Generating Extended Benchmark (Target: {TARGET_COUNT} queries)...")
    
    new_queries = []
    
    with acquire_manager() as mgr:
        # 1. Define Valid Collections based on data directory structure
        valid_collections = [
            "csweb.admin", "csweb.ai", "csweb.calendar", "csweb.news", "csweb.notice", "csweb.profs", "csweb.research",
            "notion.marketing", "notion.notice",
            "portal.job", "portal.startUp"
        ]
        
        col_list = mgr.list_collections_info()
        collections = [c['name'] for c in col_list if c['name'] in valid_collections]
        
        print(f"   Found {len(collections)} active collections: {collections}")
        
        # Calculate sample size per collection
        per_col = TARGET_COUNT // len(collections) + 5
        
        for col_name in collections:
            print(f"   extracting from {col_name}...")
            try:
                # Scroll to get docs
                hits, _ = mgr.client.scroll(
                    collection_name=col_name,
                    limit=per_col + 20,
                    with_payload=True
                )
                
                for h in hits:
                    payload = h.payload
                    doc_id = payload.get("db_id")
                    if not doc_id:
                        continue
                    
                    # Heuristic Query Generation
                    # 1. Title/Name based (Keyword)
                    title = payload.get("title") or payload.get("name")
                    if title and len(title) > 4:
                        new_queries.append({
                            "query": title,
                            "expected_doc_ids": [doc_id],
                            "origin_collection": col_name,
                            "query_type": "keyword"
                        })
                        
                    # 2. Content snippet based (Semantic-ish)
                    content = payload.get("content", "")
                    if len(content) > 50:
                        # Take a random chunk from middle
                        start = len(content) // 3
                        snippet = content[start:start+40].strip()
                        if len(snippet) > 20:
                             new_queries.append({
                                "query": f"{snippet}...",
                                "expected_doc_ids": [doc_id],
                                "origin_collection": col_name,
                                "query_type": "semantic"
                            })
                            
            except Exception as e:
                print(f"   Error in {col_name}: {e}")
    
    # Shuffle and Clip
    random.shuffle(new_queries)
    final_set = new_queries[:TARGET_COUNT]
    
    output_path = "src/tests/extended_benchmark.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_set, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Generated {len(final_set)} queries in {output_path}")

if __name__ == "__main__":
    asyncio.run(generate_benchmark())
