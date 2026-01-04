
import requests
import sys
import os

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    print("--- Testing Persistent Auth Flow ---\n")
    
    # 1. Login as Admin (Assuming 'admin' was created via CLI init)
    print("[1] Logging in as 'admin'...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "password123"})
        if resp.status_code != 200:
            print(f"FAILED: Login failed: {resp.text}")
            return
        
        token = resp.json()["access_token"]
        print(f"SUCCESS: Got token: {token[:20]}...")
    except Exception as e:
        print(f"FAILED: Connection error: {e}")
        return

    # 2. Test Authorized Search (Admin Level 3)
    print("\n[2] Testing Admin Access (Level 3)...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "query_text": "전산학부",
        "top_k": 50,
        "collections": ["notion.marketing"]
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=headers)
        if resp.status_code == 200:
            json_resp = resp.json()
            results = json_resp.get("results", []) if isinstance(json_resp, dict) else json_resp
            level_3_count = sum(1 for r in results if r.get("payload", {}).get("access_level") == 3)
            print(f"SUCCESS: Found {len(results)} docs. Level 3 docs: {level_3_count}")
        else:
            print(f"FAILED: Search denied: {resp.text}")
    except Exception as e:
         print(f"FAILED: {e}")
         
    # 3. Test Invalid Token
    print("\n[3] Testing Invalid Token...")
    bad_headers = {"Authorization": "Bearer invalid.token.123"}
    resp = requests.post(f"{BASE_URL}/query/hybrid", json=payload, headers=bad_headers)
    print(f"Response Code: {resp.status_code} (Expected 401 or Guest Access)")
    # Since we fall back to guest in middleware (non-strict), we might still get results but Level 0-1
    if resp.status_code == 200:
        json_resp = resp.json()
        results = json_resp.get("results", []) if isinstance(json_resp, dict) else json_resp
        max_level = max([r.get("payload", {}).get("access_level", 0) for r in results]) if results else 0
        print(f"Fallback Access Level Max: {max_level} (Should be <= 1 for Guest)")

if __name__ == "__main__":
    test_auth_flow()
