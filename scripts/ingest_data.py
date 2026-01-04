#!/usr/bin/env python3
import sys
import os
import json
import argparse
import asyncio
import time
from typing import List, Dict, Any
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from llm_backend.client import VectorDBClient

def normalize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw JSON into VectorDB Client format."""
    # Essential fields
    title = doc.get('title', 'Untitled')
    content = doc.get('content', '')
    
    # If no content, check for 'contents' or 'body'
    if not content:
        content = doc.get('contents', doc.get('body', ''))
    
    # Metadata: everything else
    metadata = {}
    
    # If 'metadata' key exists, use it
    if 'metadata' in doc and isinstance(doc['metadata'], dict):
        metadata.update(doc['metadata'])
    
    # Flatten other fields into metadata
    for k, v in doc.items():
        if k not in ['title', 'content', 'contents', 'metadata']:
            # Skip complex objects if needed, or convert to string
            if isinstance(v, (dict, list)):
                # Simplified handling: store as string or keep if valid JSON
                 metadata[k] = str(v)
            else:
                 metadata[k] = v
                 
    return {
        "title": title,
        "content": content,
        "metadata": metadata
    }

def find_files(path: Path) -> List[Path]:
    """Recursively find all .json and .jsonl files."""
    files = []
    if path.is_file():
        if path.suffix in ['.json', '.jsonl']:
            files.append(path)
    elif path.is_dir():
        for p in path.rglob("*"):
            if p.is_file() and p.suffix in ['.json', '.jsonl']:
                files.append(p)
    return files

def load_documents_from_files(files: List[Path]) -> List[Dict[str, Any]]:
    """Load and normalize documents from a list of files."""
    documents = []
    for p in files:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                if p.suffix == '.jsonl':
                    for line in f:
                        if line.strip():
                            raw = json.loads(line)
                            documents.append(normalize_document(raw))
                else:
                    raw = json.load(f)
                    if isinstance(raw, list):
                        for item in raw:
                            documents.append(normalize_document(item))
                    elif isinstance(raw, dict):
                        documents.append(normalize_document(raw))
        except Exception as e:
            print(f"[WARN] Skipping {p}: {e}")
            
    return documents

async def ingest_batch(client: VectorDBClient, collection: str, batch: List[Dict[str, Any]], batch_idx: int):
    """Ingest a single batch of documents."""
    try:
        response = await client.upsert_documents(
            documents=batch,
            tenant_id=collection,
        )
        
        job_id = response.get("job_id")
        if not job_id:
            # Fallback for sync responses? unlikely now but good safety
            sys.stdout.write("s") # sync
            sys.stdout.flush()
            return True

        # POLL JOB STATUS
        while True:
            status_resp = await client.get_job_status(job_id)
            job = status_resp.get("job", {})
            state = job.get("status")
            
            if state == "completed":
                sys.stdout.write(".")
                sys.stdout.flush()
                return True
            elif state == "processing":
                # Optional: show spinner or just wait silently to avoid log spam
                # sys.stdout.write("p")
                pass
            elif state == "failed":
                print(f"\n[ERROR] Batch {batch_idx+1} Job {job_id} Failed: {job.get('message')}")
                return False
            
            # Wait before polling again
            await asyncio.sleep(1.0)

    except Exception as e:
        print(f"\n[ERROR] Batch {batch_idx+1} Failed: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser(description="Ingest data into VectorDB")
    parser.add_argument("--path", required=True, help="Path to file or directory of data")
    parser.add_argument("--collection", required=True, help="Target collection name (Tenant ID in VectorDB)")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for ingestion")
    parser.add_argument("--api-url", default="http://localhost:8000", help="VectorDB API URL")
    parser.add_argument("--api-key", help="Vector API Key (optional if in env)")

    args = parser.parse_args()

    # Load API Key
    api_key = args.api_key or os.getenv("VECTOR_API_KEY")
    if not api_key:
        # Emergency fallback read .env
        try:
            with open(os.path.join(os.path.dirname(__file__), "../.env")) as f:
                 for line in f:
                    if line.startswith("VECTOR_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
        except:
            pass

    if not api_key:
        print("Error: VECTOR_API_KEY not found. Set it in .env or pass --api-key")
        sys.exit(1)

    print(f"[INFO] Starting Ingestion")
    print(f"   Source: {args.path}")
    print(f"   Target: {args.collection}")
    
    # Find files
    target_path = Path(args.path)
    if not target_path.exists():
        print(f"Error: Path {args.path} does not exist.")
        sys.exit(1)

    files = find_files(target_path)
    print(f"   Found {len(files)} files to process.")
    
    if not files:
        print("No JSON/JSONL files found.")
        sys.exit(0)

    # Load All Docs (Naive approach: load all into memory. Better for huge datasets: generators)
    # Given typical user project sizes, this might be fine, but let's be slightly efficient 
    # and just load them. If OOM issues, we'd switch to generator.
    print("[INFO] Loading documents...")
    documents = load_documents_from_files(files)
    print(f"[INFO] Prepared {len(documents)} documents for ingestion.")

    if not documents:
        print("No valid documents found.")
        sys.exit(0)

    # Initialize Client
    client = VectorDBClient(base_url=args.api_url, api_key=api_key)

    # Check Health
    try:
        if not await client.health_check():
            print("[ERROR] Cannot connect to VectorDB server. Is it running?")
            sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Connection Error: {repr(e)}")
        sys.exit(1)
    
    # Process Batches
    print(f"[INFO] Sending data to {args.api_url} (Batch Size: {args.batch_size})")
    start_time = time.time()
    total_success = 0
    total_docs = len(documents)
    
    for i in range(0, total_docs, args.batch_size):
        batch = documents[i : i + args.batch_size]
        success = await ingest_batch(client, args.collection, batch, i // args.batch_size)
        if success:
            total_success += len(batch)
            
    print("\n" + "-" * 40)
    duration = time.time() - start_time
    print(f"[INFO] Ingestion Complete in {duration:.2f}s")
    print(f"[SUCCESS] Successfully Ingested: {total_success} / {total_docs}")

if __name__ == "__main__":
    asyncio.run(main())
