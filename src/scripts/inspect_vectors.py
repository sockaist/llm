import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager


async def inspect():
    with acquire_manager() as mgr:
        print("[SEARCH] Inspecting csweb.news vectors...")
        res, _ = mgr.client.scroll(
            collection_name="csweb.news", limit=1, with_vectors=True
        )

        if not res:
            print("[FAIL] No docs found in csweb.news")
            return

        doc = res[0]
        vecs = doc.vector

        print(f"ID: {doc.id}")

        # Check Dense
        if "dense" in vecs:
            d = vecs["dense"]
            print(f"[OK] Dense: {len(d)} dim (First 5: {d[:5]})")
        else:
            print("[FAIL] Dense vector MISSING")

        # Check Sparse
        if "sparse" in vecs:
            s_ind = vecs["sparse"].indices
            vecs["sparse"].values
            print(f"[OK] Sparse (BM25): {len(s_ind)} non-zero elements")
            print(f"   Indices: {s_ind[:5]}")
        else:
            print("[FAIL] Sparse vector MISSING")

        # Check SPLADE
        if "splade" in vecs:
            sp_ind = vecs["splade"].indices
            vecs["splade"].values
            print(f"[OK] SPLADE: {len(sp_ind)} non-zero elements")
            print(f"   Indices: {sp_ind[:5]}")
        else:
            print("[FAIL] SPLADE vector MISSING")


if __name__ == "__main__":
    asyncio.run(inspect())
