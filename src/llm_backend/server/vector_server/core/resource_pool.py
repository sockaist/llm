# llm_backend/server/vector_server/core/resource_pool.py
# -*- coding: utf-8 -*-
import os
import threading
from queue import Queue
from contextlib import contextmanager
from typing import Optional
from llm_backend.utils.logger import logger
from llm_backend.vectorstore.vector_db_manager import VectorDBManager  # 실제 구현 import

# =========================
# 환경 변수
# =========================
def _pool_size_env() -> int:
    try:
        return int(os.getenv("POOL_SIZE", "3"))
    except Exception:
        return 3

def _strict_env() -> bool:
    # 호출 시점에 재평가(동적 변경 반영)
    return os.getenv("POOL_STRICT", "0") == "1"

def _acquire_timeout_env() -> float:
    try:
        return float(os.getenv("POOL_ACQUIRE_TIMEOUT", "10"))
    except Exception:
        return 10.0


# =========================
# 리소스 풀
# =========================
class ResourcePool:
    def __init__(self, pool_size: int = 3):
        self.pool_size = pool_size
        self.pool: "Queue[VectorDBManager]" = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.initialized = False

    def initialize(self):
        with self.lock:
            if self.initialized:
                logger.info("[ResourcePool] Already initialized.")
                return
            logger.info(f"[ResourcePool] Initializing {self.pool_size} VectorDBManager instances...")
            for i in range(self.pool_size):
                try:
                    mgr = VectorDBManager()
                    self.pool.put(mgr)
                    logger.info(f"[ResourcePool] Manager #{i+1} initialized")
                except Exception as e:
                    logger.error(f"[ResourcePool] Failed to initialize manager #{i+1}: {e}")
            self.initialized = True
            logger.info("[ResourcePool] Initialization complete")

    def acquire(self, block: bool = True, timeout: Optional[float] = None) -> Optional[VectorDBManager]:
        try:
            mgr = self.pool.get(block=block, timeout=timeout)
            logger.debug("[ResourcePool] Acquired VectorDBManager instance")
            return mgr
        except Exception:
            logger.warning("[ResourcePool] No available VectorDBManager (pool exhausted)")
            return None

    def release(self, mgr: VectorDBManager):
        if mgr is None:
            return
        try:
            self.pool.put(mgr)
            logger.debug("[ResourcePool] Released VectorDBManager instance")
        except Exception as e:
            logger.error(f"[ResourcePool] Failed to release instance: {e}")

    def status(self) -> dict:
        return {
            "pool_size": self.pool_size,
            "available": self.pool.qsize(),
            "in_use": self.pool_size - self.pool.qsize(),
            "initialized": self.initialized
        }


# =========================
# 전역 싱글톤
# =========================
_global_pool: Optional[ResourcePool] = None
_pool_lock = threading.Lock()

def init_vector_pool(size: int = None):
    """
    서버 시작 시 풀 초기화.
    - size 미지정 시 환경변수 POOL_SIZE 사용(기본 3)
    """
    global _global_pool
    with _pool_lock:
        if _global_pool is None:
            pool_size = size if size is not None else _pool_size_env()
            _global_pool = ResourcePool(pool_size=pool_size)
            _global_pool.initialize()
            logger.info(f"[ResourcePool] Global pool initialized (size={pool_size})")
        else:
            logger.info("[ResourcePool] Global pool already exists.")

def get_pool_status() -> dict:
    if _global_pool is None:
        return {"initialized": False, "message": "Resource pool not initialized"}
    return _global_pool.status()

def release_all():
    """
    풀 내부 인스턴스를 비웁니다. (프로세스 종료 시 호출 권장)
    """
    global _global_pool
    if _global_pool is None:
        logger.info("[ResourcePool] release_all: pool not initialized")
        return
    try:
        released = 0
        while not _global_pool.pool.empty():
            mgr = _global_pool.pool.get_nowait()
            # 필요 시 mgr.close() 등 정리 로직 호출
            released += 1
        logger.info(f"[ResourcePool] Released {released} instances")
    except Exception as e:
        logger.error(f"[ResourcePool] release_all error: {e}")


# =========================
# 컨텍스트 매니저 (STRICT 지원)
# =========================
@contextmanager
def acquire_manager(timeout: Optional[float] = None):
    """
    VectorDBManager를 풀에서 획득하는 컨텍스트 매니저.

    동작 규칙:
    - 풀 미초기화: 임시 인스턴스 생성(STRICT와 무관)
    - 풀 초기화 + 가용 없음:
        - POOL_STRICT=1 → RuntimeError("Resource pool exhausted") 발생
        - POOL_STRICT=0 → 임시 인스턴스 생성하여 처리(풀에는 반환하지 않음)
    - 정상 획득 시: 컨텍스트 종료 시 풀에 반환
    """
    def _cleanup(temp_mgr: VectorDBManager):
        try:
            if hasattr(temp_mgr, "client") and hasattr(temp_mgr.client, "close"):
                temp_mgr.client.close()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"[ResourcePool] Temp manager cleanup failed: {exc}")

    # 1) 풀이 아직 없으면 임시 인스턴스로 대응
    if _global_pool is None:
        logger.warning("[ResourcePool] Pool not initialized. Creating temporary manager (STRICT=N/A).")
        mgr = VectorDBManager()
        try:
            yield mgr
        finally:
            _cleanup(mgr)
        return

    # 2) 풀에서 획득 시도
    acquire_timeout = timeout if timeout is not None else _acquire_timeout_env()
    mgr = _global_pool.acquire(timeout=acquire_timeout)

    if mgr is None:
        strict = _strict_env()
        if strict:
            logger.error("[ResourcePool] Exhausted and POOL_STRICT=1 → raising RuntimeError")
            raise RuntimeError("Resource pool exhausted")
        logger.warning("[ResourcePool] No available manager — creating temporary instance (STRICT=0).")
        temp_mgr = VectorDBManager()
        try:
            yield temp_mgr
        finally:
            _cleanup(temp_mgr)
        return

    # 3) 정상 획득
    try:
        yield mgr
    finally:
        _global_pool.release(mgr)