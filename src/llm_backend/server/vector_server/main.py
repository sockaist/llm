# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from llm_backend.server.vector_server.api import (
    endpoints_query, endpoints_crud, endpoints_batch, endpoints_admin, endpoints_health,
    endpoints_feedback, endpoints_dictionary, endpoints_logs
)
from llm_backend.server.vector_server.core import scheduler, resource_pool
from llm_backend.server.vector_server.manager.vector_manager import run_server_auto_initialize
from llm_backend.utils.logger import logger
import os
import traceback
from contextlib import asynccontextmanager
from llm_backend.server.vector_server.api.endpoints_metrics import instrumentator # Import Instrumentator

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[Startup] Initializing Vector Server...")

    # 1) 부팅 1회 auto-init
    if os.getenv("RUN_AUTOINIT", "1") == "1":
        run_server_auto_initialize()

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

app = FastAPI(title="Vector Server", version="2.0", lifespan=lifespan)

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

from llm_backend.server.vector_server.core.security.middleware import SecurityMiddleware
from llm_backend.server.vector_server.core.security.access_control import AccessControlManager
from llm_backend.server.vector_server.config.security_config import load_configuration
from llm_backend.server.vector_server.config.security_validator import SecurityValidator
import sys

# -----------------------------
# Secure Configuration Loading
# -----------------------------
try:
    # 0. Load Configuration (Secure by Default)
    # Will default to Tier 1 if no file found (Fail Secure)
    # Or should init fail? User's request implies automatic safe defaults?
    # "Tier 1: Basic" is production ready.
    config = load_configuration("vectordb.yaml")
    
    # 1. Validate Configuration
    warnings = SecurityValidator.validate_config(config)
    blocking_warnings = [w for w in warnings if w.blocking]
    
    if blocking_warnings:
        logger.critical("❌ SECURITY CONFIGURATION ERROR: Deployment blocked.")
        for w in blocking_warnings:
             logger.critical(f"   [{w.severity.upper()}] {w.message} -> {w.recommendation}")
        sys.exit(1)
        
    for w in warnings:
        logger.warning(f"⚠️ [SECURITY WARNING] {w.message}")
        
    logger.info(f"✅ Security Configuration Loaded: Env={config.environment}, Tier={config.security.tier}")

except Exception as e:
    logger.critical(f"Fatal Error Loading Configuration: {e}")
    sys.exit(1)

# Security Manager (Layer 1)
access_manager = AccessControlManager()

app.add_middleware(
    SecurityMiddleware,
    access_manager=access_manager,
    config=config
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)

if _allow_origins:
    logger.info(f"[CORS] allow_origins={_allow_origins}")
else:
    logger.info(f"[CORS] allow_origin_regex={_allow_origin_regex}")

# -----------------------------
# 전역 예외 핸들러
# -----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[Exception] {request.method} {request.url} -> {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": str(exc)},
    )

# -----------------------------
# 라우터 등록
# -----------------------------
app.include_router(endpoints_health.router)
app.include_router(endpoints_query.router)
app.include_router(endpoints_crud.router)
app.include_router(endpoints_batch.router)
app.include_router(endpoints_admin.router)
app.include_router(endpoints_feedback.router)
app.include_router(endpoints_dictionary.router)
# Removed duplicate dictionary router if present
app.include_router(endpoints_logs.router)

# Enable Prometheus Metrics
instrumentator.instrument(app).expose(app)