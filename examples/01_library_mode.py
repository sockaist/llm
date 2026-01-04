# 01_library_mode.py
# Run this script to test "Library Mode" (Serverless) usage of VortexDB.

import sys
import os

# Ensure we can import from src
# In production installed via pip, this is not needed.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, "src")
sys.path.append(src_dir)

from llm_backend.vectorstore.vector_db_manager import VectorDBManager

def main():
    print("[INFO] Initializing VortexDB in Library Mode...")
    
    # 1. Initialize Manager directly
    #    Make sure Qdrant is running on localhost:6333
    db = VectorDBManager(
        url="http://localhost:6333",
        default_collection="sockaist",
        pipeline_config={
            "use_dense": True,
            "weights": {"dense": 0.5, "sparse": 0.3, "splade": 0.2}
        }
    )
    
    print("[OK] Initialization Complete.")

    # 2. Perform Search
    query = "장학금 신청 기간"
    print(f"\n[SEARCH] Searching for: '{query}'")
    
    try:
        results = db.search(
            query_text=query,
            top_k=3,
            alpha=0.7 # Mostly semantic
        )
        
        # 3. Print Results
        for idx, res in enumerate(results.get("results", [])):
            print(f"[{idx+1}] Score: {res['score']:.4f} | Title: {res['payload'].get('title', 'No Title')}")
            print(f"    Content: {res['payload'].get('content', '')[:100]}...")
            
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")

if __name__ == "__main__":
    main()
