
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from dotenv import load_dotenv

load_dotenv()

def run():
    client = QdrantClient(url="http://localhost:6333", api_key=os.getenv("QDRANT_API_KEY"))
    
    col = "csweb"
    
    print(f"--- Debugging Collection {col} ---")
    cnt = client.count(col)
    print(f"Total Count: {cnt}")
    
    # 1. Search without filter
    print("\n--- Raw Search (limit 5) ---")
    res = client.scroll(col, limit=5, with_payload=True)
    for p in res[0]:
        print(f"ID: {p.id} | Tenant: {p.payload.get('tenant_id')} | Access: {p.payload.get('access_level')} | Title: {p.payload.get('title')}")

    # 2. Search with Public Filter (Guest simulation)
    print("\n--- Public Filter Search ---")
    f_public = Filter(
        must=[
            FieldCondition(key="tenant_id", match=MatchValue(value="public"))
        ]
    )
    res_pub = client.scroll(col, scroll_filter=f_public, limit=5)
    print(f"Public Docs Found: {len(res_pub[0])}")
    for p in res_pub[0]:
        print(f"  > ID: {p.id}")

    # 3. Search with KAIST Filter
    print("\n--- KAIST Filter Search ---")
    f_kaist = Filter(
        must=[
            FieldCondition(key="tenant_id", match=MatchValue(value="kaist"))
        ]
    )
    # 4. Test Search Pipeline Logic Locally
    print("\n--- Pipeline Logic Test ---")
    try:
        from llm_backend.vectorstore.vector_db_manager import VectorDBManager
        from llm_backend.vectorstore.search_pipeline import run_query_pipeline
        
        mgr = VectorDBManager(client=client) # Use shared client
        
        # Mock Config
        cfg = mgr.pipeline_config
        cfg["use_dense"] = True
        
        # Run Pipeline
        results = run_query_pipeline(
            manager=mgr,
            query_text="AI",
            top_k=5,
            collections=["csweb"],
            cfg=cfg,
            user_context={"user": {"role": "guest", "id": "anonymous"}}
        )
        print(f"Pipeline returned {len(results)} results")
        for r in results:
            print(f"  > {r.get('title')}")
            
    except Exception as e:
        print(f"Pipeline Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
