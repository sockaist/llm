import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.config import FORMATS, VECTOR_SIZE

DATA_DIR = os.path.join(os.getcwd(), "data")


async def reindex_all():
    print(f"🔄 Starting Full Re-indexing (Dim: {VECTOR_SIZE})...")

    with acquire_manager() as mgr:
        # Iterate over all defined collections in config
        for col_name, config in FORMATS.items():
            print(f"\nExample: Processing {col_name}...")

            # 1. Delete Collection
            try:
                mgr.client.delete_collection(col_name)
                print(f"🗑️ Deleted {col_name}")
            except Exception as e:
                print(f"[WARN] Delete failed (maybe not exist): {e}")

            # 2. Re-create Collection with new VECTOR_SIZE
            try:
                mgr.create_collection(col_name, vector_size=VECTOR_SIZE)
                print(f"[OK] Created {col_name} (dim={VECTOR_SIZE})")
            except Exception as e:
                print(f"[FAIL] Creation failed: {e}")
                continue

            # 3. Ingest Data
            # Resolve path from col_name (e.g., notion.marketing -> data/notion/marketing)
            parts = col_name.split(".")
            if len(parts) >= 2:
                folder_path = os.path.join(DATA_DIR, parts[0], parts[1])
            else:
                # exceptional cases or custom mapping
                folder_path = os.path.join(DATA_DIR, col_name.replace(".", "/"))

            if os.path.exists(folder_path):
                print(f"📂 Ingesting from {folder_path}...")
                mgr.upsert_folder(folder_path, col_name, batch_size=32)
            else:
                print(
                    f"[WARN] Source folder not found: {folder_path} (Skipping ingest)"
                )

    print("\n✨ Full Re-indexing Complete!")


if __name__ == "__main__":
    asyncio.run(reindex_all())
