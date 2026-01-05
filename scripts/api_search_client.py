#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VortexDB API Standalone Search Client (CLI UX Version) ⚖️✨
Usage:
  python scripts/api_search_client.py --query "your query"
  python scripts/api_search_client.py --collection main (Interactive Shell)
"""

import os
import requests
import argparse
import sys
import json
from typing import List, Dict, Optional

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

class VortexAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("VECTOR_API_KEY", "default_secret")
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except:
            return False

    def search(self, query: str, collections: List[str] = ["main"], top_k: int = 5) -> Dict:
        url = f"{self.base_url}/query/hybrid"
        payload = {
            "query_text": query,
            "collections": collections,
            "top_k": top_k
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}

def print_result(result, idx):
    """Pretty print a single search result (UX matched to ./vortex search)."""
    score = result.get('avg_score', 0.0) # API returns avg_score or score? Checking...
    if 'avg_score' not in result and 'score' in result:
        score = result['score']
        
    payload = result.get('payload', {})
    content = payload.get('content', 'No content')
    
    # Metadata parsing
    meta = payload.get('metadata', {})
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except:
            meta = {}
            
    # Intelligent Title Extraction
    title = payload.get('title', 'Untitled')
    if title == 'Untitled' or not title:
        title = meta.get('name') or meta.get('title') or metadata_lookup(meta, 'title') or 'Untitled'

    print(f"\n{BOLD}{CYAN}[{idx}] {title}{RESET} {YELLOW}(Score: {score:.4f}){RESET}")
    
    # Display snippet
    snippet = content[:200] + ("..." if len(content) > 200 else "")
    print(f"    {snippet}")
    
    # Pretty Print Specific Metadata Fields
    if meta or payload:
        # Fields to display in order
        link = payload.get('link') or meta.get('link') or meta.get('web') or meta.get('url')
        display_fields = {
            "Field": meta.get('field'),
            "Major": meta.get('major'),
            "Degree": meta.get('degree'),
            "Date": meta.get('date'),
            "Web": link,
            "Mail": meta.get('mail') or meta.get('email'),
            "Office": meta.get('office'),
        }
        
        formatted_meta = [f"{BOLD}{k}:{RESET} {v}" for k, v in display_fields.items() if v]
        if formatted_meta:
            print(f"    {GREEN}Info:{RESET} {' | '.join(formatted_meta)}")

def metadata_lookup(meta, key):
    return meta.get(key)

def interactive_shell(client: VortexAPIClient, collection: str):
    print(f"\n{BOLD}Welcome to VortexDB API Search Shell{RESET}")
    print(f"Base URL: {CYAN}{client.base_url}{RESET}")
    print(f"Target Collection: {GREEN}{collection}{RESET}")
    print("Type 'exit' or 'quit' to leave. Type 'help' for commands.\n")

    current_collection = collection
    top_k = 5

    while True:
        try:
            prompt_str = f"{BOLD}vortex-api({current_collection})>{RESET} "
            user_input = input(prompt_str).strip()
            
            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit']:
                print("Bye!")
                break
            
            if user_input.lower() == 'help':
                print("\nCommands:")
                print("  :c <name>   - Change collection")
                print("  :k <num>    - Set top_k (default 5)")
                print("  <query>     - Search for query")
                continue

            if user_input.startswith(":"):
                parts = user_input.split()
                cmd = parts[0]
                
                if cmd == ":c" and len(parts) > 1:
                    current_collection = parts[1]
                    print(f"Switched to collection: {GREEN}{current_collection}{RESET}")
                elif cmd == ":k" and len(parts) > 1:
                    try:
                        top_k = int(parts[1])
                        print(f"Set top_k to: {top_k}")
                    except:
                        print(f"{RED}Invalid number{RESET}")
                else:
                    print(f"{RED}Unknown command{RESET}")
                continue

            # Search
            print(f"[*] Searching for: '{user_input}'...")
            data = client.search(user_input, collections=[current_collection], top_k=top_k)
            
            if "error" in data:
                print(f"{RED}[!] Error: {data['error']}{RESET}")
                continue

            results = data.get("results", [])
            if not results:
                print(f"{YELLOW}[!] No results found.{RESET}")
            else:
                print(f"[+] Found {len(results)} results:")
                for i, res in enumerate(results, 1):
                    print_result(res, i)
                print()

        except KeyboardInterrupt:
            print("\nType 'exit' to quit.")
        except EOFError:
            break

def main():
    parser = argparse.ArgumentParser(description="VortexDB Standalone API Search Client")
    parser.add_argument("--query", "-q", help="Search query string")
    parser.add_argument("--url", default="http://localhost:8000", help="API Base URL")
    parser.add_argument("--api-key", help="API Key")
    parser.add_argument("--collection", "-c", default="main", help="Collection name")
    parser.add_argument("--top_k", "-k", type=int, default=5, help="Number of results")

    args = parser.parse_args()

    client = VortexAPIClient(base_url=args.url, api_key=args.api_key)
    
    # Check connection
    if not client.health_check():
        print(f"{RED}[!] Cannot connect to Vortex API at {args.url}{RESET}")
        print(f"    Ensure the server is running and the URL is correct.")
        sys.exit(1)

    if args.query:
        # Single query mode
        print(f"[*] Searching for: '{args.query}'...")
        data = client.search(args.query, collections=[args.collection], top_k=args.top_k)
        
        if "error" in data:
            print(f"{RED}[!] Error: {data['error']}{RESET}")
            return

        results = data.get("results", [])
        if not results:
            print(f"{YELLOW}[!] No results found.{RESET}")
        else:
            for i, res in enumerate(results, 1):
                print_result(res, i)
    else:
        # Interactive mode
        interactive_shell(client, args.collection)

if __name__ == "__main__":
    main()
