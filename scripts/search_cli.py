#!/usr/bin/env python3
import sys
import traceback
import os
import argparse
import asyncio
import shlex
import json
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from llm_backend.client import VectorDBClient

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_result(result, idx):
    """Pretty print a single search result."""
    score = result.get('score', 0.0)
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
        # Try to find a better title in metadata
        title = meta.get('name') or meta.get('title') or meta.get('professor') or 'Untitled'

    print(f"\n{BOLD}{CYAN}[{idx}] {title}{RESET} {YELLOW}(Score: {score:.4f}){RESET}")
    print(f"    {content[:200]}..." if len(content) > 200 else f"    {content}")
    
    # Pretty Print Specific Metadata Fields
    if meta:
        # Fields to display in order (if present)
        display_fields = {
            "Field": meta.get('field'),
            "Major": meta.get('major'),
            "Degree": meta.get('degree'),
            "Date": meta.get('date'),
            "Web": meta.get('web') or meta.get('link') or meta.get('url'),
            "Mail": meta.get('mail') or meta.get('email'),
            "Phone": meta.get('phone'),
            "Office": meta.get('office'),
            "Intro": meta.get('intro')
        }
        
        # Filter out None and display
        formatted_meta = [f"{BOLD}{k}:{RESET} {v}" for k, v in display_fields.items() if v]
        
        if formatted_meta:
            print(f"    {GREEN}Info:{RESET} {' | '.join(formatted_meta)}")
            
        # ETC field (often long, print separately)
        if meta.get('etc'):
            etc = meta.get('etc').strip()
            # Truncate etc if too long
            if len(etc) > 100:
                etc = etc[:100] + "..."
            print(f"    {GREEN}Etc:{RESET}  {etc}")

async def interactive_shell(client: VectorDBClient, collection: str):
    print(f"{BOLD}Welcome to sockaist Search Shell{RESET}")
    print(f"Target Collection: {GREEN}{collection}{RESET}")
    print("Type 'exit' or 'quit' to leave. Type 'help' for commands.\n")

    current_collection = collection
    top_k = 5

    while True:
        try:
            # Custom prompt
            prompt_str = f"{BOLD}sockaist({current_collection})>{RESET} "
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

            # Command handling
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
            print(f"Searching for: '{user_input}'...")
            try:
                results = await client.search(
                    query=user_input,
                    collection_name=current_collection,
                    top_k=top_k,
                    # Hybrid search by default if client supports it
                )
                
                if not results:
                    print(f"{YELLOW}No results found.{RESET}")
                else:
                    print(f"Found {len(results)} results:")
                    for i, res in enumerate(results):
                        print_result(res, i+1)
                        
            except Exception as e:
                print(f"{RED}Search failed: {e}{RESET}")

        except KeyboardInterrupt:
            print("\nType 'exit' to quit.")
        except EOFError:
            break

async def main():
    parser = argparse.ArgumentParser(description="Interactive Search Shell")
    parser.add_argument("--collection", default="sockaist", help="Default collection name")
    parser.add_argument("--api-url", default="http://localhost:8000", help="VectorDB API URL")
    
    args = parser.parse_args()
    
    # Load API Key
    api_key = os.getenv("VECTOR_API_KEY")
    if not api_key:
        # Try to load from .env if not in environment
        # But user typically sources .env or we can just warn
        print(f"{YELLOW}Warning: VECTOR_API_KEY not set. Attempting read from .env{RESET}")
        try:
            with open(os.path.join(os.path.dirname(__file__), "../.env")) as f:
                for line in f:
                    if line.startswith("VECTOR_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        except:
             pass
    
    if not api_key:
         print(f"{RED}Error: VECTOR_API_KEY is required.{RESET}")
         sys.exit(1)

    client = VectorDBClient(base_url=args.api_url, api_key=api_key)
    
    # Check connection
    try:
        if not await client.health_check():
             print(f"{RED}Cannot connect to server at {args.api_url}{RESET}")
             sys.exit(1)
    except Exception as e:
        print(f"{RED}Connection error: {e}{RESET}")
        traceback.print_exc()
        sys.exit(1)

    await interactive_shell(client, args.collection)

if __name__ == "__main__":
    asyncio.run(main())
