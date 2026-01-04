import asyncio
import os
import sys

# Priority for local 'src'
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.collection_manager import create_collection
from llm_backend.vectorstore.vector_db_helper import create_doc_upsert


async def test_phase5():
    print("=== Testing Phase 5: Multi-Vector & ParetoRAG ===")

    col_name = "test.phase5"
    with acquire_manager() as mgr:
        # 1. Create Collection with Multi-Vector schema
        print(f"Creating collection '{col_name}'...")
        create_collection(mgr, col_name, vector_size=1024, force=True)

        # Clear Semantic Cache to avoid old results
        from llm_backend.server.vector_server.core.semantic_cache import CACHE_COLLECTION
        try:
            mgr.client.delete_collection(CACHE_COLLECTION)
            print(f"Cleared Qdrant cache '{CACHE_COLLECTION}'")
        except: pass

        # Clear Redis Cache
        try:
            from llm_backend.server.vector_server.core.cache import Cache
            redis_cache = Cache.get_instance()
            if redis_cache and hasattr(redis_cache, "redis"):
                redis_cache.redis.flushdb()
                print("Cleared Redis cache")
        except: pass

        # 2. Upsert sample documents
        sample_docs = [
            {
                "id": "doc1",
                "title": "해양학부 행정팀 연락처",
                "content": "이곳은 해양학부 행정팀입니다. 전화번호는 031-219-2700입니다. 이메일은 marine@kaist.ac.kr 입니다. "
                "입시 상담은 이민우 선생님(2710)께 문의바랍니다. 장학 관련은 박지우 선생님(2711)이 담당하십니다. "
                "졸업 요건 및 성적 문의는 김서준 선생님(2715)께 연락주세요.",
            },
            {
                "id": "doc2",
                "title": "딥러닝 연구 동향 2024",
                "content": "2024년 딥러닝 기술은 트랜스포머 아키텍처를 넘어서는 새로운 효율적 모델들이 등장하고 있습니다. "
                "특히 상태 공간 모델(SSM)과 맘바(Mamba) 아키텍처가 주목받고 있습니다. "
                "대규모 언어 모델의 경량화 기술도 급속도로 발전하고 있습니다.",
            },
        ]

        for doc in sample_docs:
            print(f"Upserting {doc['id']}...")
            create_doc_upsert(mgr.client, col_name, doc, dense_model=mgr.dense_model)

        print("Waiting for indexing...")
        import time
        time.sleep(2)

        # 3. Test Search with AutoRAG-HP
        import time
        ts = int(time.time())
        print("\n--- Search 1: Specific Entity (Title Boost Expected) ---")
        q1 = f"해양학부 연락처 {ts}"
        res1 = mgr.query(q1, top_k=3, collections=[col_name])
        if res1:
            print(f"DEBUG: First result keys: {res1[0].keys()}")
        for r in res1:
            print(
                f"- [{r['title']}] Score: {r['score']:.4f} | Rerank: {r.get('rerank_score', 'N/A')}"
            )

        print("\n--- Search 2: Topical Search (Body/Dense Priority) ---")
        q2 = f"SSM과 맘바 아키텍처에 대해 알려줘 {ts}"
        res2 = mgr.query(q2, top_k=3, collections=[col_name])
        for r in res2:
            print(
                f"- [{r['title']}] Score: {r['score']:.4f} | Rerank: {r.get('rerank_score', 'N/A')}"
            )


if __name__ == "__main__":
    asyncio.run(test_phase5())
