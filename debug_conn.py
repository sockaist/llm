
import asyncio
import httpx
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from llm_backend.client import VectorDBClient

async def main():
    print("Testing connection with manual .env parsing...")

    # Mimic search_cli.py logic
    api_key = os.getenv("VECTOR_API_KEY")
    if not api_key:
        print("Reading from .env...")
        try:
            with open(os.path.join(os.path.dirname(__file__), ".env")) as f:
                for line in f:
                    if line.startswith("VECTOR_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        print(f"Found key: '{api_key}'")
                        break
        except Exception as e:
            print(f"Failed to read .env: {e}")

    client = VectorDBClient(base_url="http://localhost:8000", api_key=api_key)
    print(f"Client headers: {client.headers}")
    
    try:
        res = await client.health_check()
        print(f"Health check success: {res}")
    except Exception as e:
        print(f"Health check failed: {type(e).__name__}")
        print(f"Error repr: {e!r}")
        print(f"Error str: '{e}'")

if __name__ == "__main__":
    asyncio.run(main())
