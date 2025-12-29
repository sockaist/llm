# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from llm_backend.server.vector_server.api import (
    endpoints_query, endpoints_crud, endpoints_batch, endpoints_admin, endpoints_health
)
from llm_backend.server.vector_server.core import scheduler, queue_manager, resource_pool
from llm_backend.server.vector_server.manager.vector_manager import run_server_auto_initialize
from llm_backend.utils.logger import logger
import os
import traceback

app = FastAPI(title="Vector Server", version="2.0")

# -----------------------------
# CORS 설정
# -----------------------------
def _parse_cors_origins():
    """
    CORS_ALLOW_ORIGINS 환경변수를 파싱합니다.
    - "https://a.com,https://b.com" 형태면 리스트 반환
    - "*" 이거나 빈 문자열이면 정규식 허용(.*)로 처리
      (allow_credentials=True일 때 Access-Control-Allow-Origin: * 금지 대응)
    """
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if raw == "" or raw == "*":
        return [], ".*"  # allow_origin_regex 사용
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins, None

_allow_origins, _allow_origin_regex = _parse_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,             # 명시 리스트
    allow_origin_regex=_allow_origin_regex,   # 전체 허용 시 정규식 사용
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
    logger.error(f"[Exception] {request.method} {request.url} → {exc}\n{traceback.format_exc()}")
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

# -----------------------------
# Lifecycle hooks
# -----------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("[Startup] Initializing Vector Server...")

    # 1) 부팅 1회 auto-init (원하면 가드 환경변수 사용)
    if os.getenv("RUN_AUTOINIT", "1") == "1":
        run_server_auto_initialize()

    # 2) 풀 초기화 (전면 채택)
    resource_pool.init_vector_pool()

    # 3) 스케줄러 (BM25 재학습 등 주기적 작업)
    # 분산 환경에서는 스케줄러를 별도 프로세스로 떼거나, 
    # API 서버 중 하나만 돌거나, Celery Beat를 써야 함.
    # 현재는 간소화를 위해 API 서버가 스케줄러도 겸임(Leader 역할)한다고 가정.
    scheduler.start_scheduler()
    
    # NOTE: Phase 2 분산 환경이므로 로컬 워커 스레드는 실행하지 않음.
    # queue_manager.start_worker() -> Removed

    logger.info("[Startup] Vector Server Ready")
    logger.info("Swagger UI available at: http://127.0.0.1:8001/docs")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("[Shutdown] Vector Server shutting down...")
    scheduler.stop_scheduler()
    # queue_manager.stop_worker() -> Removed
    resource_pool.release_all()
    logger.info("[Shutdown] Vector Server stopped gracefully")