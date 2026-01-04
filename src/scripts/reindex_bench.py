from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.collection_manager import create_collection
from llm_backend.vectorstore.vector_db_helper import create_doc_upsert
import asyncio


async def reindex_for_benchmark():
    col_src = "csweb.ai"
    col_dst = "benchmark.real.phase5"

    with acquire_manager() as mgr:
        # 1. Sample from source
        print(f"Sampling from {col_src}...")
        res, _ = mgr.client.scroll(collection_name=col_src, limit=15, with_payload=True)
        samples = []
        for p in res:
            title = p.payload.get("title")
            content = p.payload.get("content") or p.payload.get("text")
            if title and content:
                samples.append(
                    {"title": title, "content": content, "id": p.payload.get("id")}
                )

        print(f"Got {len(samples)} samples.")
        if not samples:
            return

        # 2. Re-recreate destination collection with Phase 5 schema
        print(f"Creating collection {col_dst}...")
        create_collection(mgr, col_dst, vector_size=768, force=True)

        # 3. Index with Phase 5 logic
        print(f"Indexing into {col_dst}...")
        for doc in samples:
            create_doc_upsert(mgr.client, col_dst, doc, dense_model=mgr.dense_model)

        print("Re-indexing complete.")


if __name__ == "__main__":
    asyncio.run(reindex_for_benchmark())
