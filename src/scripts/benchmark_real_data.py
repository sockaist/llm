import asyncio
import os
import sys
import time
import numpy as np
from math import sqrt
from scipy import stats

# Priority for local 'src'
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager

# Ground Truth Dataset from 'benchmark.real.phase5'
GROUND_TRUTH = [
    {"q": "딥러닝 정확도 높이는 소량 데이터 기술", "expected_title": "소량의 데이터로 딥러닝 정확도 높이는 기술"},
    {"q": "무선신호 없는 실내 치매환자 찾기", "expected_title": "카이스트가 개발한 ＇이 기술＇…무선신호 없는 실내서도 치매환자 찾아낸다"},
    {"q": "3D 객체 파트 자연어 검색 기술", "expected_title": "자연어만으로 3D객체의 part를 찾아내는 기술 개발"},
    {"q": "딥러닝 서비스 구축 비용 최소화 데이터 정제", "expected_title": "인공지능 심층 학습(딥러닝) 서비스 구축 비용 최소화 가능한 데이터 정제 기술 개발​"},
    {"q": "Stylette styling web natural language", "expected_title": "Stylette： Styling the Web with Natural Language"},
    {"q": "로봇 주행 심층 강화학습 센서 폐색", "expected_title": "심층 강화학습을 활용한 센서 폐색 하에서의 신뢰 기반 로봇 주행 기법"},
    {"q": "디지털 헬스 서비스 디자인 연구 유연한 평가", "expected_title": "사용자의 행동 변화를 지원하는 유연한 평가 기법 기반의 디지털 헬스 서비스 디자인 연구"},
    {"q": "티그리냐 언어 모델 구축 데이터셋", "expected_title": "낮은 언어자원의 한계를 극복하여  이해도가 높은 답변이 가능하게 하는  티그리냐 질문-답변 데이터셋 및 언어 모델 구축"},
    {"q": "Visual Token Matching Few-shot Learning", "expected_title": "Universal Few-shot Learning of Dense Prediction Tasks with Visual Token Matching"},
    {"q": "AtaTouch finger pinch VR controller", "expected_title": "‘AtaTouch： Robust Finger Pinch Detection for a VR Controller Using RF Return Loss’"}
]

def calculate_wilson_ci(p, n, z=1.96):
    """Wilson Score Interval for 95% CI (Binary metrics)"""
    if n == 0:
        return (0, 0)
    denom = 1 + z**2/n
    center = (p + z**2/(2*n)) / denom
    spread = z * sqrt(abs(p*(1-p)/n + z**2/(4*n**2))) / denom
    return center - spread, center + spread

async def run_statistical_benchmark():
    col_name = "benchmark.real.phase5"
    print(f"🔬 Running Statistical Benchmark on '{col_name}' (n={len(GROUND_TRUTH)})")
    
    hits = []
    mrrs = []
    latencies = []
    confidences = []

    with acquire_manager() as mgr:
        for entry in GROUND_TRUTH:
            query = entry["q"]
            expected = entry["expected_title"]
            
            start = time.time()
            # Phase 5 Search
            res = mgr.query(query, top_k=5, collections=[col_name])
            latencies.append((time.time() - start) * 1000)
            
            rank = 0
            if res:
                for i, r in enumerate(res):
                    title = r.get("payload", {}).get("title", "")
                    # Match by title (fuzzy match for whitespace/extra chars)
                    if expected.replace(" ", "") in title.replace(" ", "") or title.replace(" ", "") in expected.replace(" ", ""):
                        rank = i + 1
                        break
            
            hits.append(1 if rank == 1 else 0)
            mrrs.append(1.0/rank if rank > 0 else 0)
            confidences.append(res[0].get("score", 0) if res else 0)

    # --- Statistical Calculations ---
    n = len(hits)
    mean_hit = np.mean(hits)
    hit_ci_low, hit_ci_high = calculate_wilson_ci(mean_hit, n)
    
    mean_mrr = np.mean(mrrs)
    mrr_se = stats.sem(mrrs) if n > 1 else 0
    stats.t.interval(0.95, n-1, loc=mean_mrr, scale=mrr_se) if n > 1 and mrr_se > 0 else (mean_mrr, mean_mrr)
    
    mean_lat = np.mean(latencies)
    lat_se = stats.sem(latencies)
    lat_ci = stats.t.interval(0.95, n-1, loc=mean_lat, scale=lat_se)
    
    # Statistical Reliability Score = Wilson Lower Bound (Conservative Accuracy)
    reliability_index = (hit_ci_low * 0.8 + mean_mrr * 0.2) * 100

    print("\n" + "═"*60)
    print("📊 FINAL STATISTICAL BENCHMARK REPORT: REAL DATA")
    print("═"*60)
    print(f"🎯 Hit Rate @ 1: {mean_hit*100:.1f}%")
    print(f"   ↳ 95% Confidence Interval (Wilson): [{max(0, hit_ci_low)*100:.1f}% - {min(1, hit_ci_high)*100:.1f}%]")
    print(f"📈 Mean MRR: {mean_mrr:.3f} (Rank Consistency)")
    print(f"⚡ Avg Latency: {mean_lat:.1f}ms")
    print(f"   ↳ 95% Confidence Interval (t): [{lat_ci[0]:.1f}ms - {lat_ci[1]:.1f}ms]")
    print(f"🛡️ STATISTICAL RELIABILITY SCORE: {reliability_index:.1f} / 100")
    print("═"*60)
    print("Note: Reliability Score uses the lower bound of the CI for a conservative estimate.")

if __name__ == "__main__":
    asyncio.run(run_statistical_benchmark())
