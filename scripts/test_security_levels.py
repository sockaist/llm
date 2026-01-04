
import requests
import json

BASE_URL = "http://localhost:8000"
# Using a longer timeout and retrying once if it fails due to warming
TIMEOUT = 30

def search(role, user_id="test_user"):
    headers = {
        "x-api-key": "dev-key",
        "X-User-ID": user_id,
        "X-User-Role": role
    }
    if role == "guest":
        headers = {"x-api-key": "dev-key"}

    payload = {
        "query_text": "전산학부",
        "collections": ["demo_collection"],
        "top_k": 50
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/query/hybrid", headers=headers, json=payload, timeout=TIMEOUT)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            levels = [r.get("payload", {}).get("access_level") for r in results]
            return levels
        else:
            return f"Error: {resp.status_code} - {resp.text}"
    except Exception as e:
        return f"Exception: {e}"

if __name__ == "__main__":
    print("--- VortexDB Security Level Distribution Test ---")
    
    # 1. Guest -> Access Level <= 1
    guest_levels = search("guest", "anonymous")
    print(f"\n[Guest] Allowed Levels (Expected: 0, 1):")
    if isinstance(guest_levels, list):
        print(f"Total found: {len(guest_levels)}")
        dist = {l: guest_levels.count(l) for l in sorted(set(guest_levels))}
        print(f"Level distribution: {dist}")
    else:
        print(guest_levels)

    # 2. Viewer -> Access Level <= 2
    viewer_levels = search("viewer", "vortex_viewer")
    print(f"\n[Viewer] Allowed Levels (Expected: 0, 1, 2):")
    if isinstance(viewer_levels, list):
        print(f"Total found: {len(viewer_levels)}")
        dist = {l: viewer_levels.count(l) for l in sorted(set(viewer_levels))}
        print(f"Level distribution: {dist}")
    else:
        print(viewer_levels)

    # 3. Admin -> All Access (0, 1, 2, 3)
    admin_levels = search("admin", "admin_boss")
    print(f"\n[Admin] Allowed Levels (Expected: 0-3):")
    if isinstance(admin_levels, list):
        print(f"Total found: {len(admin_levels)}")
        dist = {l: admin_levels.count(l) for l in sorted(set(admin_levels))}
        print(f"Level distribution: {dist}")
    else:
        print(admin_levels)
