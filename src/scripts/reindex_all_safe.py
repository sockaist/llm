import asyncio
import os
import sys
import json
import gc
import psutil

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.config import FORMATS, VECTOR_SIZE
from llm_backend.vectorstore.ingest_manager import upsert_document

# Memory Limit Checker
def log_memory():
    mem = psutil.virtual_memory()
    print(f"   [MEM] Used: {mem.used / 1024 / 1024:.1f} MB ({mem.percent}%)")

DATA_DIR = os.path.join(os.getcwd(), "data")

async def reindex_all_safe():
    print(f"🔄 Starting SAFE Re-indexing (Dim: {VECTOR_SIZE})...")
    log_memory()
    
    with acquire_manager() as mgr:
        for col_name, config in FORMATS.items():
            print(f"\nExample: Processing {col_name}...")
            
            # Target collections to reindex
            # target_collections = [
            #     "csweb.news", "csweb.notice", "csweb.seminar", "csweb.event", 
            #     "csweb.research", "csweb.members", "csweb.intro",
            #     "notion.be", "notion.fe", "notion.notice", "notion.rule"
            # ]
            # Phase 10: Only reindex research for model check
            target_collections = ["csweb.research"]
            if col_name not in target_collections:
                print(f"   Skipping {col_name} (not in target_collections)")
                continue
            
            # 1. Reset Collection
            try:
                mgr.client.delete_collection(col_name)
                print(f"🗑️ Deleted {col_name}")
            except Exception:
                pass

            try:
                mgr.create_collection(col_name, vector_size=VECTOR_SIZE)
                print(f"✅ Created {col_name}")
            except Exception as e:
                print(f"❌ Creation failed: {e}")
                continue
                
            # 2. Ingest with Strict Limits
            # Resolve path
            parts = col_name.split(".")
            if len(parts) >= 2:
                folder_path = os.path.join(DATA_DIR, parts[0], parts[1])
            else:
                folder_path = os.path.join(DATA_DIR, col_name.replace(".", "/"))
            
            if not os.path.exists(folder_path):
                print(f"⚠️ Source folder not found: {folder_path} (Skipping)")
                continue

            files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
            print(f"📂 Found {len(files)} files in {folder_path}")
            
            # Manual Batch Loop
            BATCH_SIZE = 2  # Very conservative
            batch_files = []
            
            for idx, f in enumerate(files, 1):
                batch_files.append(f)
                
                if len(batch_files) >= BATCH_SIZE:
                    _process_batch_safe(mgr, col_name, folder_path, batch_files)
                    batch_files = [] 
                    
                    if idx % 10 == 0:
                        log_memory()
                        gc.collect() # Force GC
            
            # Final batch
            if batch_files:
                _process_batch_safe(mgr, col_name, folder_path, batch_files)
            
            gc.collect()
            print(f"✨ Done {col_name}")

def _process_batch_safe(mgr, col, folder, filenames):
    # Process files ONE BY ONE within the batch to avoid 'list of dicts' explosion
    # Or just loop upsert_document. 
    # upsert_document does encode() per call, which is slower but safest.
    # BGE-M3 batch encoding is faster, but if OOM happens, we fall back to serial.
    # Let's try serial upsert_document for safety.
    
    for fname in filenames:
        try:
            fpath = os.path.join(folder, fname)
            with open(fpath, 'r') as f:
                data = json.load(f)
            
            # TRUNCATION
            text = data.get("content") or data.get("contents") or ""
            if not text:
                continue
            
            # Truncate to 10k chars (approx 3-5k tokens) to be safe
            if len(text) > 10000:
                text = text[:10000]
                data["content"] = text 
                # clean up other fields if huge
            
            upsert_document(mgr, col, data)
            
        except Exception as e:
            print(f"   Error {fname}: {e}")

if __name__ == "__main__":
    asyncio.run(reindex_all_safe())
