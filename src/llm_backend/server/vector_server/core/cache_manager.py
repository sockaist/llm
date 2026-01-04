# -*- coding: utf-8 -*-
import os
import json
import time
import hashlib
from typing import Optional, Any, Dict, List
from llm_backend.utils.logger import logger

try:
    import redis
except ImportError:
    redis = None


# ============================================================
# Cache Manager (Redis → fallback to in-memory)
# ============================================================


class CacheManager:
    """
    Redis가 사용 가능하면 Redis를, 불가능하면 in-memory cache를 사용하는 캐시 매니저.
    TTL(유효 시간)을 자동 관리하며, JSON 직렬화를 통해 객체 저장 가능.
    """

    def __init__(self, ttl: int = 3600):
        # 환경 변수 기반 설정 (없으면 기본값)
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))

        self.ttl = ttl
        self._use_redis = False
        self._cache = {}
        self.client = None

        # ----------------------------------------------------
        # Redis 연결 시도
        # ----------------------------------------------------
        if redis:
            try:
                client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
                client.ping()
                self.client = client
                self._use_redis = True
                logger.info(f"[Cache] Connected to Redis at {host}:{port} (db={db})")
            except Exception as e:
                self._use_redis = False
                self.client = None
                logger.warning(
                    f"[Cache] Redis unavailable → Using in-memory fallback: {e}"
                )
        else:
            logger.warning(
                "[Cache] redis-py not installed → fallback to in-memory cache"
            )

    # --------------------------------------------------------
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """데이터를 캐시에 저장."""
        ttl = ttl or self.ttl
        try:
            # datetime/Decimal/numpy 등 비직렬화 타입을 문자열 처리
            data = json.dumps(value, default=str)
            if self._use_redis and self.client:
                self.client.setex(key, ttl, data)
            else:
                self._cache[key] = (data, time.time() + ttl)
            logger.debug(f"[Cache] Set key={key[:16]}... TTL={ttl}s")
        except Exception as e:
            logger.error(f"[Cache] Set failed: {e}")

    # --------------------------------------------------------
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회."""
        try:
            if self._use_redis and self.client:
                data = self.client.get(key)
                return json.loads(data) if data else None
            else:
                item = self._cache.get(key)
                if item:
                    data, exp = item
                    if time.time() < exp:
                        return json.loads(data)
                    else:
                        del self._cache[key]
            return None
        except Exception as e:
            logger.error(f"[Cache] Get failed: {e}")
            return None

    # --------------------------------------------------------
    def delete(self, key: str):
        """캐시 항목 삭제."""
        try:
            if self._use_redis and self.client:
                self.client.delete(key)
            else:
                self._cache.pop(key, None)
            logger.debug(f"[Cache] Deleted key={key[:16]}...")
        except Exception as e:
            logger.error(f"[Cache] Delete failed: {e}")

    # --------------------------------------------------------
    def clear(self):
        """전체 캐시 초기화."""
        try:
            if self._use_redis and self.client:
                self.client.flushdb()
            else:
                self._cache.clear()
            logger.info("[Cache] Cleared all cache entries")
        except Exception as e:
            logger.error(f"[Cache] Clear failed: {e}")

    # --------------------------------------------------------
    def backend(self) -> str:
        """현재 캐시 백엔드 정보 반환 (redis/in-memory)."""
        return "redis" if self._use_redis else "in-memory"

    @staticmethod
    def should_skip_rerank(docs: List[Dict[str, Any]], threshold: float = 0.98) -> bool:
        """
        Confidence Triage Logic.
        If the top document has a very high score (normalized 0-1), skip reranking.
        Assumes 'score' or 'avg_score' is present and roughly normalized.
        """
        if not docs:
            return False

        top_score = docs[0].get("avg_score", 0.0)
        # Assuming avg_score can be > 1.0 (RRF/Fusion), we might need to calibrate.
        # But if the logic assumes 0-1, we check.
        return top_score >= threshold


# ------------------------------------------------------------
# 전역 싱글톤 관리
# ------------------------------------------------------------
_global_cache: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """전역 CacheManager 인스턴스 반환 (초기 1회 생성)."""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache


# ============================================================
# 컬렉션별 Epoch 버전키 (정밀 캐시 무효화)
# ============================================================

# in-memory 백업용 (Redis 없을 때 사용)
_collection_epochs_mem: Dict[str, int] = {}


def get_collection_epoch(collection: str) -> int:
    cache = get_cache()
    if cache.backend() == "redis" and cache.client:
        val = cache.client.get(f"epoch:{collection}")
        return int(val) if val is not None else 0
    return _collection_epochs_mem.get(collection, 0)


def bump_collection_epoch(collection: str) -> int:
    cache = get_cache()
    if cache.backend() == "redis" and cache.client:
        new_val = int(cache.client.incr(f"epoch:{collection}"))
        logger.info(f"[Cache] Epoch bumped (redis) → {collection}={new_val}")
        return new_val
    new_v = _collection_epochs_mem.get(collection, 0) + 1
    _collection_epochs_mem[collection] = new_v
    logger.info(f"[Cache] Epoch bumped (memory) → {collection}={new_v}")
    return new_v


def bump_collections_epoch(collections: List[str]) -> None:
    for c in collections:
        bump_collection_epoch(c)


# ------------------------------------------------------------
# 캐시 키 헬퍼 (epoch 포함)
# ------------------------------------------------------------
def make_query_cache_key(q: str, cols: Optional[List[str]], k: int) -> str:
    """
    쿼리 캐시 키 생성.
    - 컬렉션은 정렬 후 조인하여 순서 불변 키를 만듭니다.
    - 각 컬렉션의 epoch을 포함하여 변경 시 자동으로 키가 달라지도록 합니다.
    """
    cols_sorted = sorted(cols or [])
    if cols_sorted:
        epochs = ",".join(f"{c}:{get_collection_epoch(c)}" for c in cols_sorted)
        cols_part = ",".join(cols_sorted)
    else:
        epochs = "none"
        cols_part = ""
    raw = f"q:{q}|cols:{cols_part}|epochs:{epochs}|k:{k}"
    return "query:" + hashlib.sha256(raw.encode()).hexdigest()
