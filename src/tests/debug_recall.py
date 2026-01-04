import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager


async def debug_query():
    query = "전산학부 윤성의 교수 연구팀은 전산학부 박대형 교수와의 공동 연구를 통해 물리적 센서 외란에 의한 센서 폐색 상에도 강인하게 모바일 내비게이션을 성공적으로 수행할 수 있도록 하는 알고리즘을 개발하였다에 대해 설명해줘"
    expected_id = "51cc882b7d5617b1ed5476782f30eb033075e66a8f5f48b350ea4226353c831b"

    with acquire_manager() as mgr:
        # Get all collections
        collections_resp = mgr.client.get_collections()
        cols = [c.name for c in collections_resp.collections]

        print(f"Query: {query}")
        print(f"Expected ID: {expected_id}")

        results = mgr.query(query, top_k=20, collections=cols)

        print("\nResults (Top 20):")
        found = False
        for i, r in enumerate(results, 1):
            db_id = r.get("db_id")
            score = r.get("score")
            avg_score = r.get("avg_score")
            title = r.get("title")
            match = " [MATCH!]" if db_id == expected_id else ""
            if db_id == expected_id:
                found = True
            print(
                f"{i:2d}. {db_id[:12]}... | Score: {score:.4f} | Avg: {avg_score:.4f} | {title}{match}"
            )

        if not found:
            print("\n[FAIL] Expected ID NOT FOUND in top 20.")

            # Let's check if it exists in the collection at all
            print("\nChecking if expected ID exists in DB...")
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            hits, _ = mgr.client.scroll(
                collection_name="csweb.ai",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="db_id", match=MatchValue(value=expected_id))
                    ]
                ),
                limit=1,
                with_payload=True,
            )
            if hits:
                print("[OK] Found expected ID in DB!")
                print("Payload Preview:", hits[0].payload.get("title"))
            else:
                print("[FAIL] Expected ID NOT FOUND in DB collection 'csweb.ai'.")


if __name__ == "__main__":
    asyncio.run(debug_query())
