import sys
import os
import asyncio

# Priority for local 'src'
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager


async def test_refinements():
    print("=== Phase 7 Refinements Verification Suite ===")

    with acquire_manager() as mgr:
        col = "benchmark.real.phase7"

        # 1. Semantic Boundaries (Anchors)
        print("\n[Test 1] Semantic Boundaries (Contextual Anchors)")
        res, _ = mgr.client.scroll(
            collection_name=col,
            limit=5,
            scroll_filter={"must": [{"key": "is_child", "match": {"value": True}}]},
        )
        for p in res:
            text = p.payload.get("text", "")
            title = p.payload.get("title", "")
            if text.startswith(f"[{title}]"):
                print(f"[OK] Success: Anchor found for '{title[:20]}...'")
            else:
                print(f"[FAIL] Failure: No anchor in text: '{text[:30]}...'")

        # 2. SmartCache (Dynamic Threshold)
        print("\n[Test 2] SmartCache Dynamic Thresholding")
        # Simple query
        query_simple = "졸업"
        print(f"Query: '{query_simple}'")
        mgr.query(query_simple, top_k=1, collections=[col])  # Trigger dynamic calc

        # Complex query
        query_complex = "전산학부 졸업을 위한 필수 전공 학점 및 논문 제출 요건"
        print(f"Query: '{query_complex}'")
        mgr.query(query_complex, top_k=1, collections=[col])  # Trigger dynamic calc
        print(
            "[TIP] Check logs for 'Dynamic threshold calculated' (Should be 0.90 vs 0.98)"
        )

        # 3. Router Normalization
        print("\n[Test 3] Metadata Router Normalization (NER-lite)")
        query_alias = "전산과 졸업"
        print(f"Query: '{query_alias}'")
        # Check if normalized to 'CS' and 'graduation'
        results = mgr.query(query_alias, top_k=5, collections=[col])
        if results and all(
            r.get("payload", {}).get("department") == "CS" for r in results
        ):
            print("[OK] Success: '전산과' normalized to 'CS' filter!")
        else:
            print("[FAIL] Failure: Normalization failed or no results.")

        # 4. Multi-hop Entity Boosting
        print("\n[Test 4] Multi-hop Entity Boosting")
        query_entity = "김정연"
        print(f"Query: '{query_entity}'")
        # Should expand to 'NLP', '인공지능'
        results = mgr.query(query_entity, top_k=5, collections=[col])
        boosted = [r for r in results if "_boost_reason" in r]
        if boosted:
            print(
                f"[OK] Success: Expanded entities triggered boosting! Sample: {boosted[0].get('_boost_reason')}"
            )
        else:
            print("[FAIL] Failure: No boosting triggered.")


if __name__ == "__main__":
    asyncio.run(test_refinements())
