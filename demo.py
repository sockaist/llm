
import os
import json
import glob
from typing import List, Dict, Any
from vectordb.client.sync_client import VectorDBClient
from vectordb.core.config import Config

# --- Visualization for User ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(Colors.CYAN + """
    ========================================
       VectorDB v2.0 - Interactive Demo
    ========================================
    """ + Colors.ENDC)

def load_all_jsons(root_dir: str) -> List[Dict[str, Any]]:
    docs = []
    print(f"Directory: {root_dir}")
    # Recursive search for json
    search_path = os.path.join(root_dir, "**", "*.json")
    files = glob.glob(search_path, recursive=True)
    
    print(f"Found {len(files)} JSON files.")
    
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                # If list, extend. If dict, append.
                if isinstance(data, list):
                    # Add simple ID if missing or use filename info
                    for i, item in enumerate(data):
                         if isinstance(item, dict):
                            item["_source"] = fpath
                            docs.append(item)
                elif isinstance(data, dict):
                    data["_source"] = fpath
                    docs.append(data)
        except Exception as e:
            print(Colors.WARNING + f"Skipping {fpath}: {e}" + Colors.ENDC)
            
    return docs

def main():
    print_banner()
    
    # 1. Initialize Client
    print(Colors.HEADER + "Step 1: Connecting to VectorDB Server..." + Colors.ENDC)
    try:
        # Override Env for Demo
        os.environ["VECTORDB_HOST"] = "127.0.0.1"
        os.environ["VECTORDB_PORT"] = "8000"
        # Force reload config? Wrapper does it.
        client = VectorDBClient()
        print(f"Connected to {client.base_url}")
    except Exception as e:
        print(Colors.FAIL + f"Connection Error: {e}" + Colors.ENDC)
        print("Please ensure server is running: python -m vectordb server start")
        return

    # 2. Ingest Data
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(data_dir):
        print(Colors.FAIL + f"Data directory not found at {data_dir}" + Colors.ENDC)
        return

    print(Colors.HEADER + f"Step 2: Loading Data from {data_dir}..." + Colors.ENDC)
    documents = load_all_jsons(data_dir)
    
    if not documents:
        print(Colors.WARNING + "No documents found." + Colors.ENDC)
    else:
        print(Colors.GREEN + f"Loaded {len(documents)} documents." + Colors.ENDC)
        print(Colors.HEADER + "Step 3: Ingesting to VectorDB..." + Colors.ENDC)
        
        # Batch Upsert
        collection_name = "demo_collection"
        batch_size = 50
        
        total = len(documents)
        for i in range(0, total, batch_size):
            batch = documents[i:i+batch_size]
            try:
                # Use wait=True to leverage the async queue and avoid HTTP timeouts
                client.upsert(collection=collection_name, documents=batch, wait=True)
                print(f"  Upserted batch {i//batch_size + 1}/{(total//batch_size)+1} ({len(batch)} docs)")
            except Exception as e:
                print(Colors.FAIL + f"  Batch failed: {e}" + Colors.ENDC)
        
        print(Colors.GREEN + "Ingestion Complete!" + Colors.ENDC)

    # 3. Interactive Search Loop
    print(Colors.HEADER + "\nStep 4: Ready for Questions!" + Colors.ENDC)
    print("Type 'exit' or 'quit' to stop.\n")
    
    while True:
        try:
            query = input(Colors.BOLD + "\nUser Query >> " + Colors.ENDC).strip()
            if query.lower() in ("exit", "quit", "q"):
                break
            if not query:
                continue
                
            print(f"Searching for: '{query}'...")
            
            # Search call
            results = client.search(
                text=query,
                collection=collection_name,
                top_k=3
            )
            
            # Display Results
            if "results" in results:
                for idx, res in enumerate(results["results"]):
                    score = res.get("score", 0.0)
                    payload = res.get("payload", {})
                    text = payload.get("_text", "")[:300] # Truncate long text
                    source = payload.get("_source", "unknown")
                    
                    print(Colors.BLUE + f"\n[Result {idx+1}] Score: {score:.4f}" + Colors.ENDC)
                    print(Colors.CYAN + f"Source: {source}" + Colors.ENDC)
                    print(f"Start of Text: {text}...")
            else:
                 print(Colors.WARNING + "No results found or error format." + Colors.ENDC)
                 print(results)
                 
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(Colors.FAIL + f"Error during search: {e}" + Colors.ENDC)

if __name__ == "__main__":
    main()
