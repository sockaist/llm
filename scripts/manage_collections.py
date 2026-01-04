
import os
import requests
from dotenv import load_dotenv

def manage_qdrant():
    load_dotenv()
    API_KEY = os.getenv("QDRANT_API_KEY")
    BASE_URL = "http://localhost:6333"
    
    headers = {"api-key": API_KEY}
    
    # List
    print("Listing Collections...")
    resp = requests.get(f"{BASE_URL}/collections", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.json()}")
    
    existing = [c['name'] for c in resp.json().get('result', {}).get('collections', [])]
    
    if "csweb" in existing:
        print("Deleting existing 'csweb'...")
        requests.delete(f"{BASE_URL}/collections/csweb", headers=headers)
        
    print("Creating 'csweb' with named vectors...")
    payload = {
        "vectors": {
            "dense": {
                "size": 1024,
                "distance": "Cosine"
            }
        },
        "sparse_vectors": {
            "sparse": {},
            "splade": {}
        }
    }
    r = requests.put(f"{BASE_URL}/collections/csweb", json=payload, headers=headers)
    print(f"Create Status: {r.status_code}")
    print(f"Create Body: {r.text}")

if __name__ == "__main__":
    manage_qdrant()
