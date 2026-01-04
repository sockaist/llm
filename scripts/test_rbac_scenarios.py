
import requests
import os
import sys

BASE_URL = "http://localhost:8000"
COLLECTION = "csweb"
QUERY = "AI" # Common term

# 1. Admin Login (to clear/setup users if needed, or just use admin)
# We assume admin exists from previous steps (admin/admin1234)
def get_token(username, password):
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
        if resp.status_code == 200:
            return resp.json()["access_token"]
        print(f"Login failed for {username}: {resp.text}")
    except Exception as e:
        print(f"Login error: {e}")
    return None

def create_user(admin_token, username, password, role="user", tenant_id="kaist"):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "username": username,
        "password": password,
        "role": role,
        "tenant_id": tenant_id
    }
    resp = requests.post(f"{BASE_URL}/users/", json=payload, headers=headers)
    if resp.status_code in [200, 201]:
        print(f"Created user {username} ({role}, {tenant_id})")
    elif resp.status_code == 400 and "already exists" in resp.text:
        print(f"User {username} already exists")
    else:
        print(f"Failed to create user {username}: {resp.text}")

def search(token=None, label="Guest"):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        req_payload = {"query_text": QUERY, "top_k": 100, "collections": [COLLECTION]}
        resp = requests.post(f"{BASE_URL}/query/hybrid", json=req_payload, headers=headers)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            count = len(results)
            print(f"[{label}] Search '{QUERY}' found {count} results.")
            # Verify secrets
            secrets = [r for r in results if "[SECRET]" in r.get("title", "")]
            if secrets:
                print(f"   !!! WARNING: {label} saw {len(secrets)} SECRET docs!")
            else:
                print(f"   (Verified: No SECRET docs visible)")
            return count
        else:
            print(f"[{label}] Search failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[{label}] Error: {e}")
    return 0

def run_tests():
    print("=== RBAC Verification Scenario ===")
    
    # 1. Get Admin Token
    admin_token = get_token("admin", "admin1234!")
    if not admin_token:
        print("Critical: Cannot login as admin.")
        return

    # 2. Create Test Users
    # - User A: Tenant KAIST (Should see Public + KAIST)
    # - User B: Tenant OTHER (Should see Public only, NOT KAIST) -> Optional, stick to simple for now
    create_user(admin_token, "kaist_user", "password", role="user", tenant_id="kaist")
    
    # 3. Get User Tokens
    user_token = get_token("kaist_user", "password")
    
    # 4. Scenario A: Guest (No Token)
    print("\n--- Scenario A: Guest Access ---")
    c_guest = search(token=None, label="Guest")
    
    # 5. Scenario B: Customer (KAIST User)
    print("\n--- Scenario B: KAIST User Access ---")
    c_user = search(token=user_token, label="KAIST User")
    
    # 6. Scenario C: Admin Access
    print("\n--- Scenario C: Admin Access ---")
    c_admin = search(token=admin_token, label="Admin")
    
    print("\n=== Summary ===")
    print(f"Guest Found: {c_guest}")
    print(f"User  Found: {c_user}")
    print(f"Admin Found: {c_admin}")
    
    if c_user > c_guest:
        print("SUCCESS: User sees more private data than Guest.")
    else:
        print("FAIL: User count not greater than Guest (Data might not be ingested yet or policy fail).")

if __name__ == "__main__":
    run_tests()
