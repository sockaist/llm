# -*- coding: utf-8 -*-
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends

from llm_backend.server.vector_server.api import (
    endpoints_query,
    endpoints_crud,
    endpoints_batch,
    endpoints_admin,
    endpoints_health,
    endpoints_feedback,
    endpoints_dictionary,
    endpoints_logs,
    endpoints_auth,
)
from llm_backend.server.vector_server.core import scheduler, resource_pool
from llm_backend.server.vector_server.manager.vector_manager import (
    run_server_auto_initialize,
)
from llm_backend.vectorstore.sparse_engine import init_sparse_engine
from llm_backend.vectorstore.config import BM25_PATH
from llm_backend.utils.logger import logger
from llm_backend.server.vector_server.api.endpoints_metrics import instrumentator

from llm_backend.server.vector_server.core.security.middleware import SecurityMiddleware
from llm_backend.server.vector_server.core.security.audit_middleware import (
    AuditMiddleware,
)
from llm_backend.server.vector_server.core.security.access_control import (
    AccessControlManager,
)
from llm_backend.server.vector_server.config.security_config import load_configuration
from llm_backend.server.vector_server.config.security_validator import SecurityValidator
from llm_backend.server.vector_server.core.error_handler import register_error_handlers

# Environment flag for debug mode
DEBUG_MODE = os.getenv("VECTORDB_DEBUG", "0") == "1"


# -----------------------------
# Lifespan Context
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[Startup] Initializing Vector Server...")

    # 1) 부팅 1회 auto-init
    if os.getenv("RUN_AUTOINIT", "1") == "1":
        run_server_auto_initialize()

    # 1.5) BM25 Auto-Train (Cold Start)
    if not os.path.exists(BM25_PATH):
        logger.info("[Startup] BM25 model not found. Checking for data to train...")
        if os.path.exists("./data") and os.listdir("./data"):
             logger.info("[Startup] Data found. Starting initial BM25 training...")
             try:
                 init_sparse_engine(data_path="./data", force_retrain=True)
                 logger.info("[Startup] BM25 initial training complete.")
             except Exception as e:
                 logger.error(f"[Startup] BM25 training failed: {e}")
        else:
             logger.warning("[Startup] No data found in ./data. BM25 will remain uninitialized.")

    # 2) 풀 초기화
    resource_pool.init_vector_pool()

    # 3) 스케줄러
    scheduler.start_scheduler()

    logger.info("[Startup] Vector Server Ready")
    logger.info("Swagger UI available at: http://127.0.0.1:8001/docs")

    yield

    logger.info("[Shutdown] Vector Server shutting down...")
    scheduler.stop_scheduler()
    resource_pool.release_all()
    logger.info("[Shutdown] Vector Server stopped gracefully")


# -----------------------------
# Secure Configuration Loading
# -----------------------------
try:
    config = load_configuration("vectordb.yaml")

    warnings = SecurityValidator.validate_config(config)
    blocking_warnings = [w for w in warnings if w.blocking]

    if blocking_warnings:
        logger.critical("SECURITY CONFIGURATION ERROR: Deployment blocked.")
        for w in blocking_warnings:
            logger.critical(
                f"   [{w.severity.upper()}] {w.message} -> {w.recommendation}"
            )
        sys.exit(1)

    for w in warnings:
        logger.warning(f"[SECURITY WARNING] {w.message}")

    logger.info(
        f"Security Configuration Loaded: Env={config.environment}, Tier={config.security.tier}"
    )

    # Security Manager (Layer 1) - Initialize with config
    access_manager = AccessControlManager(config=config)

except Exception as e:
    logger.critical(f"Fatal Error Loading Configuration: {e}")
    sys.exit(1)


# -----------------------------
# Security & Middleware Setup
# -----------------------------

# Security Manager is now initialized inside the try block above


# Conditional debug dependency (only in debug mode)
async def _debug_dependency(request: Request):
    """Debug logging for requests - only active when VECTORDB_DEBUG=1"""
    if DEBUG_MODE:
        logger.debug(f"[DEBUG] Request: {request.method} {request.url}")


# Build dependencies list based on environment
_dependencies = [Depends(_debug_dependency)] if DEBUG_MODE else []

app = FastAPI(
    title="Vector Server", version="2.0", lifespan=lifespan, dependencies=_dependencies
)

# Add Middleware (Last added runs FIRST)
# Order: SecurityMiddleware (outer) -> AuditMiddleware (inner)
app.add_middleware(AuditMiddleware)
app.add_middleware(SecurityMiddleware, access_manager=access_manager, config=config)

logger.info("Security middleware initialized")


# -----------------------------
# CORS 설정
# -----------------------------
def _parse_cors_origins():
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if raw == "" or raw == "*":
        return [], ".*"  # allow_origin_regex 사용
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins, None


_allow_origins, _allow_origin_regex = _parse_cors_origins()

if _allow_origins:
    logger.info(f"[CORS] allow_origins={_allow_origins}")
else:
    logger.info(f"[CORS] allow_origin_regex={_allow_origin_regex}")

# Optional: Add CORS as middleware if needed, but usually better to let SecurityMiddleware handle logic if it does CORS.
# If SecurityMiddleware bypasses CORS check for OPTIONS, it's fine.
# For now, relying on SecurityMiddleware (Standard).


# -----------------------------
# 에러 핸들러 등록
# -----------------------------
register_error_handlers(app)

# -----------------------------
# 라우터 등록
# -----------------------------
app.include_router(endpoints_auth.router)
app.include_router(endpoints_health.router)
app.include_router(endpoints_query.router)
app.include_router(endpoints_crud.router)
app.include_router(endpoints_batch.router)
app.include_router(endpoints_admin.router)
app.include_router(endpoints_feedback.router)
app.include_router(endpoints_dictionary.router)
app.include_router(endpoints_logs.router)

# Enable Prometheus Metrics
instrumentator.instrument(app).expose(app)
