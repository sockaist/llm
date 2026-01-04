import os
import requests
import sys

# Configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
VECTOR_API_KEY = os.getenv("VECTOR_API_KEY", "dev-key")
DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))


def ingest_all():
    print(f"Scanning data root: {DATA_ROOT}")
    if not os.path.exists(DATA_ROOT):
        print("Data root not found!")
        sys.exit(1)

    headers = {
        "x-api-key": VECTOR_API_KEY,
        # "x-admin-secret": ... # optional
    }

    # Walk through all directories
    for root, dirs, files in os.walk(DATA_ROOT):
        json_files = [f for f in files if f.endswith(".json")]
        if not json_files:
            continue

        # Determine collection name from relative path
        rel_path = os.path.relpath(root, DATA_ROOT)
        if rel_path == ".":
            collection_name = "default"
        else:
            # e.g. "notion/marketing" -> "notion.marketing"
            collection_name = rel_path.replace(os.path.sep, ".")

        print(
            f"Triggering ingestion for '{rel_path}' -> '{collection_name}' ({len(json_files)} files)..."
        )

        try:
            # 1. Ensure collection exists
            try:
                requests.post(
                    f"{API_URL}/admin/collections/create",
                    json={"name": collection_name, "vector_size": 768},
                    headers=headers,
                )
            except Exception:
                pass

            # 2. Trigger Batch Upsert
            # Note: Batch endpoint might accept API key too, good practice to send it.
            resp = requests.post(
                f"{API_URL}/batch/upsert",
                json={"folder": root, "collection": collection_name},
                headers=headers,
            )
            resp.raise_for_status()
            job_info = resp.json()
            print(f" [SUCCESS] Job queued: {job_info.get('job_id')}")
        except Exception as e:
            print(f" [ERROR] Failed to trigger {rel_path}: {e}")


if __name__ == "__main__":
    ingest_all()
