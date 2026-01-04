"""
벤치마크 프레임워크
- 응답 시간, 처리량, 메모리 사용량, 검색 품질(Recall/Precision) 측정
- 각 최적화 전후 비교 데이터 수집
"""

import time
import psutil
import asyncio
from typing import List, Dict
from dataclasses import dataclass
import json
from datetime import datetime
import numpy as np
import os


@dataclass
class BenchmarkResult:
    """벤치마크 결과를 구조화"""

    timestamp: str
    phase: str  # "baseline", "quantization", "hybrid_search" 등
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    qps: float  # Queries per second
    memory_mb: float
    recall_at_10: float
    precision_at_10: float
    ndcg_at_10: float  # Normalized Discounted Cumulative Gain
    avg_confidence: float  # Average confidence score


class PerformanceBenchmark:
    def __init__(self, test_queries_path: str = "src/tests/test_queries.json"):
        """
        test_queries.json 형식:
        [
            {
                "query": "머신러닝이란?",
                "expected_doc_ids": ["doc_123", "doc_456"],  # 관련 문서 ID
                "query_type": "semantic"  # semantic, keyword, hybrid
            }
        ]
        """
        self.test_queries = self._load_test_queries(test_queries_path)
        self.results_history = []

    def _load_test_queries(self, path: str) -> List[Dict]:
        if not os.path.exists(path):
            print(f"Warning: Test queries file not found at {path}")
            return []
        with open(path, "r") as f:
            return json.load(f)

    async def run_latency_benchmark(self, vector_db, num_queries: int = None) -> Dict:
        """
        응답 시간 측정
        - 각 쿼리를 순차 실행하여 평균/P95/P99 계산
        - 콜드 스타트 제거를 위해 웜업 쿼리 10개 먼저 실행
        """
        if not self.test_queries:
            return {"avg": 0, "p95": 0, "p99": 0, "min": 0, "max": 0}

        if num_queries is None:
            num_queries = len(self.test_queries)

        latencies = []

        # Warm-up: 캐시 워밍
        print("Warming up...")
        for _ in range(min(10, len(self.test_queries))):
            await vector_db.search(self.test_queries[0]["query"])

        # 실제 측정
        print(f"Running latency test ({num_queries} queries)...")
        for i in range(num_queries):
            query = self.test_queries[i % len(self.test_queries)]["query"]
            start = time.perf_counter()
            await vector_db.search(query, top_k=10)
            latency = (time.perf_counter() - start) * 1000  # ms
            latencies.append(latency)

        return {
            "avg": sum(latencies) / len(latencies),
            "p95": self._percentile(latencies, 95),
            "p99": self._percentile(latencies, 99),
            "min": min(latencies),
            "max": max(latencies),
        }

    async def run_throughput_benchmark(
        self, vector_db, duration_sec: int = 60
    ) -> float:
        """
        처리량 측정 (QPS)
        - 지정된 시간 동안 최대한 많은 쿼리 병렬 처리
        - 실제 프로덕션 부하 시뮬레이션
        """
        if not self.test_queries:
            return 0.0

        print(f"Running throughput test ({duration_sec}s)...")
        query_count = 0
        start_time = time.time()

        async def worker():
            nonlocal query_count
            while time.time() - start_time < duration_sec:
                query = self.test_queries[query_count % len(self.test_queries)]["query"]
                await vector_db.search(query)
                query_count += 1

        # 10개 워커로 병렬 처리
        await asyncio.gather(*[worker() for _ in range(10)])

        return query_count / duration_sec

    async def run_quality_benchmark(self, vector_db) -> Dict:
        """
        검색 품질 측정
        - Recall@K: 관련 문서를 얼마나 찾았는가
        - Precision@K: 찾은 문서 중 관련 문서 비율
        - NDCG@K: 순위까지 고려한 품질
        """
        if not self.test_queries:
            return {
                "recall_at_10": 0,
                "precision_at_10": 0,
                "ndcg_at_10": 0,
                "avg_confidence": 0.0,
            }

        print("Running quality benchmark...")
        recall_scores = []
        precision_scores = []
        ndcg_scores = []
        confidence_scores = []

        for test_case in self.test_queries:
            if not test_case.get("expected_doc_ids"):
                continue

            results = await vector_db.search(test_case["query"], top_k=10)

            # Extract IDs and Scores
            # Result objects usually have .id and .score attributes
            result_ids = []
            top_score = 0.0

            if results:
                # Check structure of first result to handle object vs dict
                first = results[0]
                if hasattr(first, "score"):
                    top_score = first.score
                elif isinstance(first, dict):
                    top_score = first.get("score", 0.0)

                confidence_scores.append(top_score)

                result_ids = [
                    r.id if hasattr(r, "id") else r.get("id") for r in results
                ]
            else:
                confidence_scores.append(0.0)

            expected_ids = set(test_case["expected_doc_ids"])

            # Recall@10
            hits = len(set(result_ids) & expected_ids)
            recall = hits / len(expected_ids) if expected_ids else 0
            recall_scores.append(recall)

            # Precision@10
            precision = hits / 10
            precision_scores.append(precision)

            # NDCG@10
            ndcg = self._calculate_ndcg(result_ids, expected_ids, k=10)
            ndcg_scores.append(ndcg)

        if not recall_scores:
            return {
                "recall_at_10": 0,
                "precision_at_10": 0,
                "ndcg_at_10": 0,
                "avg_confidence": 0.0,
            }

        return {
            "recall_at_10": sum(recall_scores) / len(recall_scores),
            "precision_at_10": sum(precision_scores) / len(precision_scores),
            "ndcg_at_10": sum(ndcg_scores) / len(ndcg_scores),
            "avg_confidence": sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0,
        }

    async def run_memory_benchmark(self, vector_db) -> float:
        """
        메모리 사용량 측정
        - 쿼리 실행 중 최대 메모리 사용량
        """
        if not self.test_queries:
            return 0.0

        print("Running memory benchmark...")
        process = psutil.Process()
        baseline = process.memory_info().rss / 1024 / 1024
        max_memory = baseline

        num_queries = min(len(self.test_queries), 50)  # Limit memory check to 50
        for i in range(num_queries):
            query = self.test_queries[i % len(self.test_queries)]["query"]
            await vector_db.search(query)
            memory = process.memory_info().rss / 1024 / 1024  # MB
            max_memory = max(max_memory, memory)

        return max_memory

    async def run_full_benchmark(self, vector_db, phase_name: str) -> BenchmarkResult:
        """전체 벤치마크 실행 및 결과 저장"""
        print(f"\n{'=' * 50}")
        print(f"Running benchmark for phase: {phase_name}")
        print(f"{'=' * 50}\n")

        latency = await self.run_latency_benchmark(vector_db)
        qps = await self.run_throughput_benchmark(vector_db)
        quality = await self.run_quality_benchmark(vector_db)
        memory = await self.run_memory_benchmark(vector_db)

        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            phase=phase_name,
            avg_latency_ms=latency["avg"],
            p95_latency_ms=latency["p95"],
            p99_latency_ms=latency["p99"],
            qps=qps,
            memory_mb=memory,
            recall_at_10=quality["recall_at_10"],
            precision_at_10=quality["precision_at_10"],
            ndcg_at_10=quality["ndcg_at_10"],
            avg_confidence=quality.get("avg_confidence", 0.0),
        )

        self.results_history.append(result)
        self._save_results()
        self._print_results(result)

        return result

    def _save_results(self):
        """결과를 JSON 파일로 저장"""
        os.makedirs("src/tests", exist_ok=True)
        try:
            with open("src/tests/benchmark_results.json", "w") as f:
                # Convert dataclass to dict
                json.dump([vars(r) for r in self.results_history], f, indent=2)
        except Exception as e:
            print(f"Failed to save benchmark results: {e}")

    def _print_results(self, result: BenchmarkResult):
        """결과를 콘솔에 출력"""
        print(f"\n📊 Benchmark Results - {result.phase}")
        print(
            f"├─ Latency: {result.avg_latency_ms:.1f}ms (P95: {result.p95_latency_ms:.1f}ms)"
        )
        print(f"├─ Throughput: {result.qps:.1f} QPS")
        print(f"├─ Memory: {result.memory_mb:.1f} MB")
        print(f"├─ Recall@10: {result.recall_at_10:.3f}")
        print(f"├─ NDCG@10: {result.ndcg_at_10:.3f}")
        print(f"└─ Avg Confidence: {result.avg_confidence:.3f}\n")

    def compare_phases(self, baseline: str, optimized: str):
        """두 phase 간 성능 비교"""
        try:
            baseline_result = next(
                r for r in self.results_history if r.phase == baseline
            )
            optimized_result = next(
                r for r in self.results_history if r.phase == optimized
            )
        except StopIteration:
            print("Comparison failed: Phase not found in history.")
            return

        print(f"\n📈 Performance Improvement: {baseline} → {optimized}")
        print(
            f"├─ Latency: {self._improvement(baseline_result.avg_latency_ms, optimized_result.avg_latency_ms)}"
        )
        print(
            f"├─ Throughput: {self._improvement(baseline_result.qps, optimized_result.qps, inverse=True)}"
        )
        print(
            f"├─ Memory: {self._improvement(baseline_result.memory_mb, optimized_result.memory_mb)}"
        )
        print(
            f"└─ Recall: {self._improvement(baseline_result.recall_at_10, optimized_result.recall_at_10, inverse=True)}\n"
        )

    def _improvement(self, before: float, after: float, inverse: bool = False) -> str:
        """개선율 계산 (inverse=True면 증가가 좋음)"""
        if before == 0:
            return "N/A"
        if inverse:
            pct = ((after - before) / before) * 100
            return f"{pct:+.1f}% {'[OK]' if pct > 0 else '[FAIL]'}"
        else:
            pct = ((before - after) / before) * 100
            # for latency/memory, lower is better (negative pct is good)
            return f"{pct:+.1f}% {'[OK]' if pct < 0 else '[FAIL]'}"

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]

    @staticmethod
    def _calculate_ndcg(result_ids: List[str], expected_ids: set, k: int) -> float:
        """NDCG 계산 - 순위를 고려한 검색 품질"""
        dcg = sum(
            [
                1 / np.log2(i + 2)
                for i, doc_id in enumerate(result_ids[:k])
                if doc_id in expected_ids
            ]
        )
        idcg = sum([1 / np.log2(i + 2) for i in range(min(k, len(expected_ids)))])
        return dcg / idcg if idcg > 0 else 0
