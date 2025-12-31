import asyncio
import os
import sys
import time
import numpy as np

# Priority for local 'src'
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.collection_manager import create_collection
from llm_backend.vectorstore.vector_db_helper import create_doc_upsert
from qdrant_client.models import VectorParams, Distance

# Ground Truth Dataset
TEST_DATA = [
    {"id": "admin_1", "title": "교무처 학사팀", "content": "학사운영, 성적관리, 졸업심사 관련 업무를 담당합니다. 전화: 042-350-2345"},
    {"id": "admin_2", "title": "학생처 장학팀", "content": "장학금 지급, 국가장학금 신청, 학자금 대출 업무를 담당합니다. 전화: 042-350-2346"},
    {"id": "research_1", "title": "딥러닝 최신 연구", "content": "2024년 딥러닝은 고성능 트랜스포머 아키텍처와 SSM 기반의 효율적 모델링이 핵심입니다."},
    {"id": "research_2", "title": "해양 기상 관측 기술", "content": "해양 기상 관측을 위한 자율 운항 선박 및 센서 네트워크 기술이 발전하고 있습니다."}
]

QUERIES = [
    {"q": "학사팀 전화번호", "expected": "admin_1", "type": "entity"},
    {"q": "장학금 신청 방법", "expected": "admin_2", "type": "entity"},
    {"q": "2024년 딥러닝 동향", "expected": "research_1", "type": "topical"},
    {"q": "바다 기상 관측 센서", "expected": "research_2", "type": "topical"}
]

async def run_benchmark():
    col_name = "benchmark.phase5"
    print(f"🚀 Initializing Phase 5 Benchmark on '{col_name}'...")
    
    with acquire_manager() as mgr:
        # 1. Setup Collection
        extra = {"image": VectorParams(size=512, distance=Distance.COSINE)}
        create_collection(mgr, col_name, vector_size=768, force=True, extra_vectors=extra)
        
        # 2. Indexing Data
        for doc in TEST_DATA:
            create_doc_upsert(mgr.client, col_name, doc, dense_model=mgr.dense_model)
        
        # 3. Execution & Metrics
        results = []
        for q_entry in QUERIES:
            query = q_entry["q"]
            expected = q_entry["expected"]
            
            start = time.time()
            # Phase 5 Search (AutoRAG-HP is internal in query pipeline)
            search_res = mgr.query(query, top_k=5, collections=[col_name])
            latency = (time.time() - start) * 1000
            
            # Metrics Collection
            top_hit = search_res[0] if search_res else None
            rank = 0
            if top_hit:
                print(f"  [Debug] Query: {query} | Top Result ID: {top_hit.get('id')} | Payload ID: {top_hit.get('payload', {}).get('id')}")
            
            for i, res in enumerate(search_res):
                # Search in both level-1 id and payload id
                if res.get("id") == expected or res.get("payload", {}).get("id") == expected:
                    rank = i + 1
                    break
            
            hit = 1 if rank == 1 else 0
            mrr = 1.0 / rank if rank > 0 else 0
            confidence = top_hit["score"] if top_hit else 0
            
            results.append({
                "query": query,
                "hit": hit,
                "mrr": mrr,
                "latency": latency,
                "confidence": confidence,
                "type": q_entry["type"]
            })

        # 4. Aggregation
        avg_hit = np.mean([r["hit"] for r in results])
        avg_mrr = np.mean([r["mrr"] for r in results])
        avg_latency = np.mean([r["latency"] for r in results])
        avg_conf = np.mean([r["confidence"] for r in results])
        
        # Reliability Index = Accuracy * Confidence * Consistency (Proxy: MRR)
        reliability = (avg_hit * 0.4 + avg_mrr * 0.4 + avg_conf * 0.2) * 100

        print("\n" + "="*40)
        print("📊 PHASE 5 BENCHMARK RESULTS")
        print("="*40)
        print(f"✅ Hit Rate @ 1: {avg_hit*100:.1f}%")
        print(f"📈 MRR: {avg_mrr:.3f}")
        print(f"⚡ Avg Latency: {avg_latency:.1f}ms")
        print(f"🛡️ Avg Confidence: {avg_conf:.3f}")
        print(f"⭐ INTEGRATED RELIABILITY INDEX: {reliability:.1f}/100")
        print("="*40)

        # 5. Intent Isolation Results
        entity_hit = np.mean([r["hit"] for r in results if r["type"] == "entity"])
        topical_hit = np.mean([r["hit"] for r in results if r["type"] == "topical"])
        print("\n[AutoRAG-HP Breakdown]")
        print(f"- Entity Search Hit: {entity_hit*100:.1f}% (Title Boosted)")
        print(f"- Topical Search Hit: {topical_hit*100:.1f}% (Body/Recall Strategy)")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
