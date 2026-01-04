# src/tests/test_security_perf.py
import pytest
import time
import asyncio
from llm_backend.server.vector_server.core.security.audit_logger import audit_logger
from llm_backend.server.vector_server.core.security.defense import defense_system


@pytest.mark.asyncio
async def test_logging_overhead():
    """
    Verify Logging Overhead < 5ms for Tier 2 events (Async).
    """
    iterations = 1000
    start_time = time.time()

    for i in range(iterations):
        await audit_logger.log_event("perf_test_event", {"i": i})

    end_time = time.time()
    total_time = end_time - start_time
    avg_latency = (total_time / iterations) * 1000  # ms

    print(f"\n[Perf] Tier 2 Logging Overhead: {avg_latency:.4f} ms/op")
    assert avg_latency < 5.0, f"Logging too slow: {avg_latency} ms"


@pytest.mark.asyncio
async def test_defense_overhead():
    """
    Verify Defense Logic Overhead < 1ms (In-Memory).
    """
    user_id = "user123"
    query = "test query for overhead measurement"
    vector = [0.1] * 128

    iterations = 1000
    start_time = time.time()

    for _ in range(iterations):
        defense_system.validate_request(user_id, query=query, vector=vector)

    end_time = time.time()
    total_time = end_time - start_time
    avg_latency = (total_time / iterations) * 1000  # ms

    print(f"\n[Perf] Defense Check Overhead: {avg_latency:.4f} ms/op")
    assert avg_latency < 1.0, f"Defense too slow: {avg_latency} ms"


@pytest.mark.asyncio
async def test_concurrency_load():
    """
    Simulate 1000 Concurrent Requests logging events.
    Verify no errors and reasonable throughput.
    """
    concurrent_reqs = 1000

    async def worker(idx):
        await audit_logger.log_event("load_test", {"worker": idx})

    start_time = time.time()
    tasks = [worker(i) for i in range(concurrent_reqs)]
    await asyncio.gather(*tasks)
    end_time = time.time()

    duration = end_time - start_time
    qps = concurrent_reqs / duration
    print(
        f"\n[Perf] Concurrency: {concurrent_reqs} reqs in {duration:.4f}s = {qps:.2f} QPS"
    )

    # 1000 requests in async queue should be extremely fast (<< 1s total for enqueue)
    assert duration < 2.0
