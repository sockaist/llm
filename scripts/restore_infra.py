#!/usr/bin/env python3
import os
import sys
import glob
import re
import requests
import subprocess
import time

QDRANT_URL = "http://localhost:6333"
REDIS_CONTAINER = "vortex_redis"

def log(msg):
    print(f"[RESTORE] {msg}")

def restore_redis(backup_dir):
    rdb_path = os.path.join(backup_dir, "redis_dump.rdb")
    if not os.path.exists(rdb_path):
        log(f"No redis_dump.rdb found in {backup_dir}, skipping Redis restore.")
        return

    log("Restoring Redis...")
    try:
        # 1. Stop Redis
        subprocess.check_call(["docker", "stop", REDIS_CONTAINER])
        
        # 2. Copy dump
        subprocess.check_call(["docker", "cp", rdb_path, f"{REDIS_CONTAINER}:/data/dump.rdb"])
        
        # 3. Start Redis
        subprocess.check_call(["docker", "start", REDIS_CONTAINER])
        log("Redis restored successfully.")
        
        # Wait for Redis to be ready
        time.sleep(2)
    except Exception as e:
        log(f"Error restoring Redis: {e}")

def restore_qdrant(backup_dir):
    # Find all snapshot files: qdrant_{collection}_{snapshot_name}
    # Pattern: qdrant_(.+?)_(.+)
    files = glob.glob(os.path.join(backup_dir, "qdrant_*"))
    if not files:
        log(f"No Qdrant snapshots found in {backup_dir}, skipping Qdrant restore.")
        return

    log(f"Found {len(files)} Qdrant snapshots to restore.")
    
    for fpath in files:
        fname = os.path.basename(fpath)
        # Regex to parse collection name
        match = re.match(r"qdrant_(.+?)_(.+)", fname)
        if not match:
            log(f"Skipping unknown file format: {fname}")
            continue
            
        col_name = match.group(1)
        # Qdrant restores often require deleting the existing collection first or using a special endpoint
        # Simple strategy: 
        # 1. Upload snapshot -> This usually recovers it if using the 'recover' param or endpoint conventions.
        #    Actual API: POST /collections/{collection_name}/snapshots/upload
        #    "Recover the collection from the uploaded snapshot file."
        
        log(f"Restoring collection: {col_name} from {fname}")
        try:
            with open(fpath, "rb") as f:
                # Based on Qdrant API docs, this uploads and recovers
                url = f"{QDRANT_URL}/collections/{col_name}/snapshots/upload"
                resp = requests.post(url, files={"snapshot": f})
                resp.raise_for_status()
                log(f"Successfully restored {col_name}")
        except Exception as e:
            log(f"Failed to restore {col_name}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 restore_infra.py <BACKUP_DIRECTORY>")
        sys.exit(1)
        
    backup_dir = sys.argv[1]
    if not os.path.isdir(backup_dir):
        print(f"Error: {backup_dir} is not a directory")
        sys.exit(1)

    restore_redis(backup_dir)
    restore_qdrant(backup_dir)
    log("Restore process completed.")

if __name__ == "__main__":
    main()
