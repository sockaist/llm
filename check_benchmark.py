from vectordb.client.sync_client import VectorDBClient
import os

os.environ["VECTORDB_HOST"] = "127.0.0.1"
os.environ["VECTORDB_PORT"] = "8000"

def check():
    client = VectorDBClient()
    print(f"Searching demo_collection for 'benchmark'...")
    res = client.search(text="benchmark", collection="demo_collection", top_k=10)
    
    results = res.get("results", [])
    print(f"Found {len(results)} results.")
    
    for idx, r in enumerate(results):
        payload = r.get("payload", {})
        source = payload.get("_source", "unknown")
        score = r.get("score", 0.0)
        text = payload.get("_text", "")[:100]
        print(f"[{idx+1}] Source: {source} | Score: {score:.4f} | Text: {text}...")

if __name__ == "__main__":
    check()
