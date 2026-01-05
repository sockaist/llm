#!/usr/bin/env python3
"""
Stand-alone Remote Ingestion Script for Vortex VectorDB.
Can be run from anywhere, independent of the project structure.
Requires: pip install httpx
"""
import os
import sys
import json
import asyncio
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Try importing httpx, else exit with instruction
try:
    import httpx
except ImportError:
    print("Error: 'httpx' library is missing.")
    print("Please install it running: pip install httpx")
    sys.exit(1)


class RemoteVectorClient:
    """Minimal Client for VectorDB API."""
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["x-api-key"] = api_key
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=60.0)

    async def close(self):
        await self.client.aclose()

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get("/health")
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"[Client] Health Check Failed: {e}")
            return False

    async def ingest_batch(self, collection: str, documents: List[Dict[str, Any]]) -> Optional[str]:
        """Sends a batch of documents to the Async Queue. Returns Job ID."""
        payload = {
            "collection": collection,
            "documents": documents
        }
        try:
            # Note: Using the new /batch/ingest endpoint
            resp = await self.client.post("/batch/ingest", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("job_id")
        except httpx.HTTPStatusError as e:
            print(f"[Client] API Error: {e.response.text}")
            return None
        except Exception as e:
            print(f"[Client] Request Error: {e}")
            return None

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        try:
            resp = await self.client.get(f"/batch/jobs/status/{job_id}")
            resp.raise_for_status()
            return resp.json().get("job", {})
        except Exception:
            return {}


def normalize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw JSON into VectorDB Client format."""
    title = doc.get('title', 'Untitled')
    content = doc.get('content', '')
    
    if not content:
        content = doc.get('contents', doc.get('body', ''))
    
    metadata = {}
    if 'metadata' in doc and isinstance(doc['metadata'], dict):
        metadata.update(doc['metadata'])
    
    for k, v in doc.items():
        if k not in ['title', 'content', 'contents', 'metadata']:
            if isinstance(v, (dict, list)):
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


async def poll_job(client: RemoteVectorClient, job_id: str, batch_idx: int):
    """Polls a job until completion."""
    sys.stdout.write(f"\n   [Batch {batch_idx}] Job {job_id} Queued. Polling")
    while True:
        job = await client.get_job_status(job_id)
        status = job.get("status")
        
        if status == "completed":
            sys.stdout.write(" [OK]\n")
            return True
        elif status == "failed":
            sys.stdout.write(f" [FAILED]: {job.get('message')}\n")
            return False
        
        sys.stdout.write(".")
        sys.stdout.flush()
        await asyncio.sleep(1.0)


async def main():
    parser = argparse.ArgumentParser(description="Remote Data Ingestion Tool for Vortex VectorDB")
    parser.add_argument("--path", required=True, help="Path to data file or directory")
    parser.add_argument("--collection", required=True, help="Target Collection Name")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL (e.g. http://192.168.1.100:8000)")
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch Size")

    args = parser.parse_args()
    
    # Resolve API Key
    api_key = args.api_key
    if not api_key:
        api_key = os.getenv("VECTOR_API_KEY")
    if not api_key:
        print("[ERROR] No API Key provided. Use --api-key or VECTOR_API_KEY env var.")
        sys.exit(1)

    # 1. Setup
    print(f"=== Remote Ingestion Tool ===")
    print(f"Target: {args.api_url}")
    print(f"Collection: {args.collection}")
    print(f"Path: {os.path.abspath(args.path)}")
    
    target = Path(args.path)
    if not target.exists():
        print(f"[ERROR] Path not found: {target}")
        sys.exit(1)
        
    # 2. Find Files
    print("[1/4] Scanning files...")
    files = find_files(target)
    print(f"      Found {len(files)} JSON/JSONL files.")
    if not files:
        sys.exit(0)

    # 3. Load Data
    print("[2/4] Loading and normalizing data...")
    docs = load_documents_from_files(files)
    print(f"      Loaded {len(docs)} documents.")
    if not docs:
        sys.exit(0)

    # 4. Ingest Loop
    print(f"[3/4] Ingesting in batches of {args.batch_size}...")
    client = RemoteVectorClient(args.api_url, api_key)
    
    if not await client.health_check():
        print("[ERROR] Server unreachble.")
        await client.close()
        sys.exit(1)

    total = len(docs)
    success_count = 0
    
    batch_idx = 1
    for i in range(0, total, args.batch_size):
        chunk = docs[i : i + args.batch_size]
        job_id = await client.ingest_batch(args.collection, chunk)
        
        if job_id:
            success = await poll_job(client, job_id, batch_idx)
            if success:
                success_count += len(chunk)
        else:
            print(f"   [Batch {batch_idx}] Failed to enqueue.")
            
        batch_idx += 1
        
    await client.close()
    
    print("\n[4/4] Summary")
    print(f"      Total Documents: {total}")
    print(f"      Successfully Ingested: {success_count}")
    print("=== Done ===")

if __name__ == "__main__":
    asyncio.run(main())
