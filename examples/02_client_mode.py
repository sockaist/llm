# 02_client_mode.py
# Run this script to test "Client Mode" usage (Connecting to API Server).

import sys
import os
import time

# Ensure we can import locally
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from vectordb.client.sync_client import VectorDBClient

def main():
    print("[INFO] Connecting to VortexDB Server...")
    
    # 1. Initialize Client
    #    This assumes the server is running on http://localhost:8000
    try:
        # Use the Master API Key defined in docker-compose.yml
        client = VectorDBClient(api_key="vortex-secret-key-123")
        print(f"[OK] Connected to {client.base_url}")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    # 2. Ingest Data (Upsert)
    print("\n[INFO] Uploading sample data...")
    docs = [
        {"id": "ex_1", "title": "Example Doc 1", "content": "This is a test document for client mode.", "date": "2024-01-01"},
        {"id": "ex_2", "title": "Example Doc 2", "content": "Another document to verify search.", "date": "2024-01-02"}
    ]
    
    try:
        # wait=True ensures we block until processing is done
        client.upsert(collection="sockaist", documents=docs, wait=True)
        print("[OK] Upsert successful.")
    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
             print(f"[ERROR] Upsert failed: {e}")
             print(f"        Server Response: {e.response.text}")
        else:
             print(f"[ERROR] Upsert failed (Check auth?): {e}")

    # 3. Search Data
    query = "test document"
    print(f"\n[SEARCH] Searching for: '{query}'")
    
    try:
        results = client.search(
            text=query,
            collection="sockaist",
            top_k=2
        )
        
        for idx, res in enumerate(results.get("results", [])):
            payload = res.get("payload", {})
            print(f"[{idx+1}] Score: {res['score']:.4f} | Title: {payload.get('title')}")
            
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")

if __name__ == "__main__":
    main()
