from fastapi import APIRouter
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

router = APIRouter(tags=["Metrics"])

# Custom Metrics
VECTOR_SEARCH_LATENCY = Histogram(
    "vector_search_latency_seconds",
    "Latency of vector search operations",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
)

CACHE_HIT_TOTAL = Counter(
    "cache_hit_total",
    "Number of cache hits",
    labelnames=["cache_type"],  # e.g., "l1_memory", "l2_redis", "semantic"
)

# Instrumentator instance (to be exposed in main.py)
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[],
)


@router.get("/metrics")
def get_metrics():
    """
    Exposes Prometheus metrics.
    Note: The instrumentator usually exposes this automatically on app startup via .expose(app).
    However, we define the router here to allow explicit inclusion if needed,
    though instrumentator.expose() handles the route internally.
    We will just return a simple status here, relying on main.py to wire expose().
    """
    return {"status": "Metrics exposed at /metrics (via Instrumentator)"}
