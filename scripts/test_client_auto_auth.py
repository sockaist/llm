
from vectordb.client.sync_client import VectorDBClient
import sys

def test_auto_auth():
    print("--- Testing Client Auto-Auth ---\n")
    
    # Initialize WITHOUT api_key
    print("[1] Initializing VectorDBClient (no args)...")
    client = VectorDBClient(base_url="http://localhost:8000")
    
    if client.api_key:
        print(f"SUCCESS: Auto-detected API Key: {client.api_key[:15]}...")
    else:
        print("FAILED: No API Key detected.")
        sys.exit(1)

    # Validate actual access
    try:
        print("[2] Fetching Collection List (Requires Auth)...")
        colls = client.list_collections()
        print(f"SUCCESS: Collections found: {colls}")
    except Exception as e:
        print(f"FAILED: Access denied or error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_auto_auth()
