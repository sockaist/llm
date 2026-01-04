import asyncio
import os
import sys
import json
import random

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.ingest_manager import upsert_document
from llm_backend.vectorstore.config import VECTOR_SIZE

TARGET_COLS = ["csweb.news", "csweb.research"]
DATA_DIR = os.path.join(os.getcwd(), "data/csweb")


async def prepare_comparison():
    print("[INFO] Preparing Comparison Baseline...")

    with acquire_manager() as mgr:
        # 1. Check counts
        for col in TARGET_COLS:
            try:
                # mgr.client.get_collection might fail if not exists
                try:
                    info = mgr.client.get_collection(col)
                    count = (
                        info.vectors_count
                        if info.vectors_count is not None
                        else info.points_count
                    )
                except Exception:
                    count = 0

                print(f"[{col}] Current Count: {count}")

                if count < 20:
                    print(
                        f"[WARN] [{col}] count low (or missing). Creating & Ingesting subset..."
                    )

                    # Ensure collection exists (Force create if missing/empty)
                    try:
                        mgr.create_collection(col, vector_size=VECTOR_SIZE)
                        print(f"   -> Created collection {col} (dim={VECTOR_SIZE})")
                    except Exception as e:
                        print(f"   -> Create collection warning: {e}")

                    # Ingest logic
                    folder_name = col.split(".")[1]  # news or research
                    source_dir = os.path.join(DATA_DIR, folder_name)

                    files = [f for f in os.listdir(source_dir) if f.endswith(".json")]
                    subset = files[:50]  # Limit to 50 files
                    print(f"   -> Ingesting {len(subset)} files from {source_dir}")

                    for fname in subset:
                        with open(os.path.join(source_dir, fname), "r") as f:
                            data = json.load(f)
                            # Normalize
                            text = data.get("content") or data.get("contents") or ""
                            if not text:
                                continue

                            doc_payload = {
                                "content": text,
                                "title": data.get("title"),
                                "date": data.get("date"),
                                "id": data.get("id") or fname,
                                "collection": col,
                            }
                            # Use upsert_document function
                            upsert_document(mgr, col, doc_payload)
            except Exception as e:
                print(f"[{col}] Error checking/ingesting: {e}")

    # 2. Generate Queries (Reuse generate_test_data logic but restricted)
    print("\n[SEARCH] Generating Comparison Queries...")
    # We need to hack or call it. It writes to file.
    # Let's just import and modify or rewrite small logic here.

    queries = []

    with acquire_manager() as mgr:
        for col in TARGET_COLS:
            # Fetch points
            points, _ = mgr.client.scroll(
                collection_name=col, limit=30, with_payload=True
            )

            for p in points:
                text = (
                    p.payload.get("content")
                    or p.payload.get("contents")
                    or p.payload.get("text")
                )
                if not text or len(text) < 50:
                    continue

                # Create a simple keyword query
                # Simulating "Extract keywords"
                words = text.split()
                if len(words) > 5:
                    q_text = " ".join(words[:5]) + "?"
                    queries.append(
                        {
                            "query": q_text,
                            "expected_doc_ids": [p.payload.get("db_id") or p.id],
                            "origin_collection": col,
                            "query_type": "keyword",
                        }
                    )

    # Save
    random.shuffle(queries)
    final_queries = queries[:50]

    out_path = "src/tests/comparison_queries.json"
    with open(out_path, "w") as f:
        json.dump(final_queries, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved {len(final_queries)} queries to {out_path}")


if __name__ == "__main__":
    asyncio.run(prepare_comparison())
