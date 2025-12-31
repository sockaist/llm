from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.collection_manager import create_collection
from llm_backend.vectorstore.vector_db_helper import create_doc_upsert
import asyncio

async def reindex_for_phase7():
    col_src = 'csweb.ai'
    col_dst = 'benchmark.real.phase7'
    
    with acquire_manager() as mgr:
        # 1. Sample from source
        print(f"Sampling from {col_src}...")
        res, _ = mgr.client.scroll(collection_name=col_src, limit=15, with_payload=True)
        samples = []
        for p in res:
            title = p.payload.get('title')
            content = p.payload.get('content') or p.payload.get('text')
            if title and content:
                samples.append({'title': title, 'content': content, 'id': p.payload.get('id')})
        
        print(f"Got {len(samples)} samples.")
        if not samples:
            return
            
        # 2. Re-create destination collection
        print(f"Creating collection {col_dst}...")
        create_collection(mgr, col_dst, vector_size=768, force=True)
        
        # 3. Index with Phase 7 logic (includes Parent-Child)
        print(f"Indexing into {col_dst}...")
        for i, doc in enumerate(samples):
            # Phase 7 Refinement: Tag some docs with test metadata for routing verification
            if i < 5:
                doc['department'] = 'CS'
                doc['category'] = 'graduation'
                doc['year'] = '2024'
                
            create_doc_upsert(mgr.client, col_dst, doc, dense_model=mgr.dense_model)
            
        print("Phase 7 Re-indexing complete.")

if __name__ == "__main__":
    asyncio.run(reindex_for_phase7())
