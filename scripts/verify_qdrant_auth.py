
import os
import sys
import requests
from dotenv import load_dotenv

def verify_qdrant_security():
    load_dotenv()
    
    API_KEY = os.getenv("QDRANT_API_KEY")
    HOST = os.getenv("VECTORDB_HOST", "localhost")
    PORT = os.getenv("VECTORDB_PORT", "6333") # Qdrant default port usually 6333
    BASE_URL = f"http://{HOST}:{PORT}"
    
    print(f"--- Verifying Qdrant Security at {BASE_URL} ---\n")
    
    if not API_KEY:
        print("[ERROR] QDRANT_API_KEY not found in environment.")
        sys.exit(1)

    # 1. Test Unauthorized Access (Should Fail)
    print("[1] Testing Unauthorized Access (No Key)...")
    try:
        resp = requests.get(f"{BASE_URL}/collections", timeout=2)
        if resp.status_code in [401, 403]:
            print(f"SUCCESS: Access Denied as expected (Status: {resp.status_code})")
        else:
            print(f"FAILED: Request succeeded without key! (Status: {resp.status_code})")
            print("CRITICAL: Qdrant is NOT secured. Did you restart it with the new config?")
            # We don't exit here, we want to see if the key works at least
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to Qdrant. Is it running?")
        sys.exit(1)

    # 2. Test Authorized Access (Should Succeed)
    print("\n[2] Testing Authorized Access (With Key)...")
    headers = {"api-key": API_KEY}
    try:
        resp = requests.get(f"{BASE_URL}/collections", headers=headers, timeout=2)
        if resp.status_code == 200:
            print("SUCCESS: Access Granted with valid key.")
            print(f"Collections: {resp.json().get('result', {}).get('collections', [])}")
        else:
            print(f"FAILED: Key rejected (Status: {resp.status_code})")
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    verify_qdrant_security()
