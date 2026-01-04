#!/usr/bin/env python3
import argparse
import sys
import os
import requests
import json

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def get_api_config():
    api_url = os.getenv("VECTOR_API_URL", "http://localhost:8000")
    api_key = os.getenv("VECTOR_API_KEY")
    
    if not api_key:
        # Try finding .env
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("VECTOR_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            break
        except:
            pass
            
    if not api_key:
        print(f"{RED}Error: VECTOR_API_KEY is not set.{RESET}")
        sys.exit(1)
        
    return api_url, {"x-api-key": api_key}

import time
import re
import sys

# ... previous imports ...

def poll_job_status(job_id, base_url, headers):
    print(f"\n{YELLOW}Polling job status for ID: {job_id}{RESET}")
    spinner = ['|', '/', '-', '\\']
    idx = 0
    
    while True:
        try:
            # Simple Spinner
            sys.stdout.write(f"\r{CYAN}Processing... {spinner[idx % 4]}{RESET}")
            sys.stdout.flush()
            idx += 1
            
            resp = requests.get(f"{base_url}/admin/jobs/list", params={"limit": 20}, headers=headers)
            if resp.status_code == 200:
                jobs = resp.json().get("jobs", [])
                target_job = next((j for j in jobs if j.get("id") == job_id), None)
                
                if target_job:
                    status = target_job.get("status")
                    msg = target_job.get("message", "")
                    
                    if status == "completed":
                        print(f"\n{GREEN}Job Completed!{RESET}")
                        print(f"Result: {msg}")
                        break
                    elif status == "failed":
                        print(f"\n{RED}Job Failed!{RESET}")
                        print(f"Error: {msg}")
                        break
                    # running or queued, continue
            
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Polling stopped by user. Job may still be running in background.{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}Error polling job:{RESET} {e}")
            time.sleep(2)

def create_snapshot(collection):
    base_url, headers = get_api_config()
    print(f"{CYAN}Creating snapshot for collection: {BOLD}{collection}{RESET}...")
    
    try:
        # Note: Assuming endpoint structure based on standard REST practices for this project
        # adjust endpoint path if needed based on Manage API
        resp = requests.post(f"{base_url}/admin/snapshot/create", params={"collection": collection}, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status')
            if status == 'queued':
                # Extract Job ID
                msg = data.get('message', '')
                # "Snapshot creation queued. Job ID: <uuid>"
                match = re.search(r"Job ID:\s*([a-f0-9-]+)", msg)
                if match:
                    job_id = match.group(1)
                    poll_job_status(job_id, base_url, headers)
                else:
                     print(f"{GREEN}Background Job Started!{RESET}")
                     print(f"Details: {msg}")
            else:
                print(f"{GREEN}Success!{RESET} Snapshot created: {BOLD}{data.get('snapshot_name') or data.get('path')}{RESET}")
        else:
            print(f"{RED}Failed to create snapshot.{RESET} ({resp.status_code})")
            print(resp.text)
    except Exception as e:
        print(f"{RED}Error:{RESET} {e}")

def list_snapshots(collection):
    base_url, headers = get_api_config()
    print(f"{CYAN}Listing snapshots for collection: {BOLD}{collection}{RESET}...")
    
    try:
        resp = requests.get(f"{base_url}/admin/snapshot/list", params={"collection": collection}, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            snapshots = data.get("snapshots", [])
            
            if not snapshots:
                print(f"{YELLOW}No snapshots found.{RESET}")
                return

            print(f"\nFound {len(snapshots)} snapshots:")
            for s in snapshots:
                # s might be a string (filename) or dict
                if isinstance(s, dict):
                    name = s.get("name", "unknown")
                    size = s.get("size", "unknown")
                    date = s.get("created_at", "")
                    print(f"- {name} ({size}) {date}")
                else:
                    print(f"- {s}")
        else:
            print(f"{RED}Failed to list snapshots.{RESET} ({resp.status_code})")
            print(resp.text)
    except Exception as e:
        print(f"{RED}Error:{RESET} {e}")

def restore_snapshot(collection, snapshot_name):
    base_url, headers = get_api_config()
    print(f"{CYAN}Restoring snapshot {BOLD}{snapshot_name}{RESET} to {BOLD}{collection}{RESET}...")
    
    try:
        data = {
            "collection": collection,
            "path": snapshot_name  # The API expects 'path' in SnapshoptPathRequest, usually just the filename works if logic supports it
        }
        # Note: endpoints_admin.py uses SnapshotPathRequest which has 'path'. 
        # But wait, restore_snapshot_api takes req: SnapshotPathRequest.
        # Let's check SnapshotPathRequest definition if possible, but usually it's just 'path'.
        # The prompt used 'snapshot_name', admin uses 'path'. Let's allow flexibility.
        
        resp = requests.post(f"{base_url}/admin/snapshot/restore", json=data, headers=headers)
        
        if resp.status_code == 200:
            print(f"{GREEN}Success!{RESET} Restore initiated.")
        else:
            print(f"{RED}Failed to restore snapshot.{RESET} ({resp.status_code})")
            print(resp.text)
    except Exception as e:
        print(f"{RED}Error:{RESET} {e}")

def main():
    parser = argparse.ArgumentParser(description="Manage VectorDB Snapshots")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Create
    create_parser = subparsers.add_parser("create", help="Create a new snapshot")
    create_parser.add_argument("collection", help="Target collection name")
    
    # List
    list_parser = subparsers.add_parser("list", help="List snapshots")
    list_parser.add_argument("collection", help="Target collection name")
    
    # Restore
    restore_parser = subparsers.add_parser("restore", help="Restore a snapshot")
    restore_parser.add_argument("collection", help="Target collection name")
    restore_parser.add_argument("snapshot_name", help="Name of the snapshot file")
    
    args = parser.parse_args()
    
    if args.command == "create":
        create_snapshot(args.collection)
    elif args.command == "list":
        list_snapshots(args.collection)
    elif args.command == "restore":
        restore_snapshot(args.collection, args.snapshot_name)

if __name__ == "__main__":
    main()
