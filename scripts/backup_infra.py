#!/usr/bin/env python3
import os
import sys
import time
import requests
import subprocess
import shutil
from datetime import datetime

# Configuration
BACKUP_ROOT = "./backups"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = os.path.join(BACKUP_ROOT, TIMESTAMP)
QDRANT_URL = "http://localhost:6333"
REDIS_CONTAINER = "vortex_redis"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def backup_redis():
    log("Backing up Redis...")
    try:
        # 1. Trigger Save
        subprocess.check_call(["docker", "exec", REDIS_CONTAINER, "redis-cli", "SAVE"])
        
        # 2. Copy dump.rdb
        dest = os.path.join(BACKUP_DIR, "redis_dump.rdb")
        subprocess.check_call(["docker", "cp", f"{REDIS_CONTAINER}:/data/dump.rdb", dest])
        log(f"Redis backup saved to {dest}")
    except subprocess.CalledProcessError as e:
        log(f"Error backing up Redis: {e}")

def backup_qdrant():
    log("Backing up Qdrant Collections...")
    try:
        # 1. List Collections
        resp = requests.get(f"{QDRANT_URL}/collections")
        resp.raise_for_status()
        collections = resp.json().get("result", {}).get("collections", [])
        
        for col in collections:
            name = col["name"]
            log(f"Snapshotting collection: {name}")
            
            # 2. Create Snapshot
            snap_resp = requests.post(f"{QDRANT_URL}/collections/{name}/snapshots")
            snap_resp.raise_for_status()
            snapshot_name = snap_resp.json().get("result", {}).get("name")
            
            if not snapshot_name:
                log(f"Failed to get snapshot name for {name}")
                continue
                
            # 3. Download Snapshot
            # Note: Qdrant snapshots are stored in /snapshots directory inside container or exposed via API
            # Downloading via API
            download_url = f"{QDRANT_URL}/collections/{name}/snapshots/{snapshot_name}"
            # Need strict stream downloading for large files
            local_filename = os.path.join(BACKUP_DIR, f"qdrant_{name}_{snapshot_name}")
            
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            log(f"Downloaded snapshot: {local_filename}")
            
    except Exception as e:
        log(f"Error backing up Qdrant: {e}")

def main():
    ensure_dir(BACKUP_DIR)
    log(f"Starting backup to {BACKUP_DIR}")
    
    backup_redis()
    backup_qdrant()
    
    log("Backup completed.")

if __name__ == "__main__":
    main()
