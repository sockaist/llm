
import requests
import json

BASE_URL = "http://localhost:8000"
# Master API key from env/config (defaulting to dev-key for now as per auth.py fallback)
API_KEY = "dev-key" 

def test_access(name, headers, path="/query/hybrid", method="POST", data=None):
    print(f"\n--- Testing: {name} ---")
    url = f"{BASE_URL}{path}"
    try:
        if method == "POST":
            resp = requests.post(url, headers=headers, json=data, timeout=5)
        elif method == "GET":
            resp = requests.get(url, headers=headers, timeout=5)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, json=data, timeout=5)
        
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Success! Result count: {len(resp.json().get('results', []))}")
        else:
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_payload = {
        "query_text": "전산학부",
        "collections": ["demo_collection"],
        "top_k": 3
    }

    # 1. Admin Search
    test_access("Admin Search", {
        "x-api-key": API_KEY,
        "X-User-ID": "admin_boss",
        "X-User-Role": "admin"
    }, data=search_payload)

    # 2. Viewer Search
    test_access("Viewer Search", {
        "x-api-key": API_KEY,
        "X-User-ID": "vortex_viewer",
        "X-User-Role": "viewer"
    }, data=search_payload)

    # 3. Viewer Deletion (Should be Forbidden 403)
    delete_payload = {
        "collection": "demo_collection",
        "db_id": "any-id"
    }
    test_access("Viewer Delete (Expect 403)", {
        "x-api-key": API_KEY,
        "X-User-ID": "vortex_viewer",
        "X-User-Role": "viewer"
    }, path="/crud/delete", method="POST", data={"collection": "demo_collection", "db_id": "test"})

    # 4. Unauthenticated Search (Expect 401 or 403)
    test_access("No API Key Search (Expect 4xx)", {}, data=search_payload)

    print("\nSecurity Test Complete.")
