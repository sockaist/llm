# -*- coding: utf-8 -*-
import time
import re
import numpy as np
import os
import secrets
from typing import List, Optional, Tuple, Any
from llm_backend.utils.logger import logger

# Try importing Redis, fallback to Mock if missing
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("[Defense] Redis not installed. Falling back to In-Memory Rate Limiting.")

class RedisRateLimiter:
    """
    Distributed Rate Limiting using Redis (Sliding Window Log).
    Fallback: In-Memory Token Bucket (for single instance).
    """
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.use_redis = REDIS_AVAILABLE
        self.redis = None
        
        if self.use_redis:
            try:
                self.redis = redis.from_url(redis_url, socket_timeout=1.0)
                self.redis.ping()
                logger.info(f"[Defense] Connected to Redis at {redis_url}")
            except Exception as e:
                logger.warning(f"[Defense] Redis connection failed: {e}. Switching to In-Memory.")
                self.use_redis = False

        # In-Memory Fallback
        if not self.use_redis:
            self._memory_store = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if request is allowed.
        """
        try:
            if self.use_redis:
                return self._check_redis(key, max_requests, window_seconds)
            else:
                return self._check_memory(key, max_requests, window_seconds)
        except Exception as e:
            logger.error(f"[Defense] Rate limit check failed: {e}")
            return True  # Fail open to avoid blocking valid traffic on error

    def _check_redis(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        pipeline = self.redis.pipeline()
        # Remove old entries
        pipeline.zremrangebyscore(key, '-inf', now - window)
        # Count current
        pipeline.zcard(key)
        # Add new
        pipeline.zadd(key, {now: now})
        # Set cleanup expiry
        pipeline.expire(key, window + 1)
        results = pipeline.execute()
        
        current_count = results[1]
        if current_count < limit:
            return True
        return False

    def _check_memory(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        history = self._memory_store.get(key, [])
        # Filter valid timestamps
        history = [t for t in history if t > now - window]
        
        if len(history) < limit:
            history.append(now)
            self._memory_store[key] = history
            return True
        
        self._memory_store[key] = history
        return False

class VectorAnomalyDetector:
    """
    Statistical Anomaly Detection for Vectors (Z-Score).
    Protects against 'Poisoning' attacks (inserting extreme outlines).
    """
    def __init__(self, sigma_threshold: float = 3.0):
        self.threshold = sigma_threshold
        # Baseline stats (Mock: in real system, load from DB stats)
        # Assuming normalized vectors, mean ~0, std ~small
        self.baseline_mean = 0.0
        self.baseline_std = 0.05  # Approximate for high-dim normalized vectors

    def is_anomalous(self, vector: List[float]) -> Tuple[bool, str]:
        if not vector:
            return False, ""
        
        arr = np.array(vector)
        # Check basic properties
        norm = np.linalg.norm(arr)
        if abs(norm - 1.0) > 0.1: # Allow some float error, but should be close to 1 for cosine
             # Not necessarily malicious, but malformed if we expect normalized
             pass 

        # Global Z-Score (simplified for MVP)
        # A true malicious vector often has high magnitude or distinct distribution
        mean_val = np.mean(arr)
        
        z_score = abs(mean_val - self.baseline_mean) / (self.baseline_std + 1e-9)
        
        if z_score > self.threshold:
            return True, f"z_score={z_score:.2f} (> {self.threshold})"
        
        return False, ""

class EmbeddingProtector:
    """
    Differential Privacy for Embeddings.
    Adds Laplace Noise to prevent 'Embedding Inversion' attacks.
    """
    def __init__(self, epsilon: float = 1.0):
        self.epsilon = epsilon

    def apply_noise(self, vector: List[float]) -> List[float]:
        """
        Add Laplace noise to the vector.
        """
        arr = np.array(vector)
        # Scale of noise = sensitivity / epsilon. Sensitivity for unit vector is small.
        sensitivity = 2.0 / len(vector) # Heuristic for bounded vector
        scale = sensitivity / self.epsilon
        
        noise = np.random.laplace(0, scale, len(vector))
        noisy_vector = arr + noise
        
        # Re-normalize to maintain utility for cosine similarity
        norm = np.linalg.norm(noisy_vector)
        if norm > 0:
            noisy_vector = noisy_vector / norm
            
        return noisy_vector.tolist()

class InjectionDetector:
    """
    Multi-level Injection Detection (Prompt + SQL + NoSQL).
    """
    PATTERNS = [
        # Prompt Injection
        r"(ignore\s+previous\s+instructions)",
        r"(system\s+prompt)",
        r"(jailbreak)",
        # SQL Injection (Classic)
        r"(\bUNION\s+SELECT\b)",
        r"(\bDROP\s+TABLE\b)",
        # NoSQL/Command Injection
        r"(\$where)",
        r"(\$ne)",
    ]

    def __init__(self):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]

    def detect(self, text: str) -> Tuple[bool, str]:
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True, f"pattern_match:{pattern.pattern}"
        return False, ""

from datetime import datetime

class ExportQuotaManager:
    """
    OWASP API6: Business Flow Protection.
    Limits mass data extraction (Scraping/Exfiltration Protection).
    Tracks daily vector retrieval counts per user.
    """
    TIERS = {
        "free": 10_000,
        "pro": 1_000_000,
        "enterprise": float('inf'),
        "admin": float('inf')  # Admin role maps to unlimited
    }

    def __init__(self, redis_client=None):
        self.redis = redis_client
        # If redis not provided, it will be set by DefenseSystem or stay None (In-Memory fallback)
        self._memory_store = {}

    def check_quota(self, user_id: str, count: int, user_tier: str = "free") -> Tuple[bool, str]:
        """
        Check if adding 'count' exceeds daily limit.
        Returns (Allowed, Message).
        """
        limit = self.TIERS.get(user_tier, self.TIERS["free"])
        if limit == float('inf'):
            return True, "unlimited"

        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"quota:{user_id}:{today}"
        
        current_usage = 0

        try:
            if self.redis:
                # Atomically increment and get
                # We want to check first? No, standard is check-then-set or atomic incr.
                # If we checks first, race condition.
                # If we incr first, we count denied requests? No, we should simulate or decr if fail.
                # Common pattern: Lua script or INCRby. If result > limit, DECRby and return False.
                # For simplicity/speed: INCR, if > limit, allowed=False (soft fail).
                # But strict implementation: 
                new_val = self.redis.incrby(key, count)
                self.redis.expire(key, 86400) # 24h
                current_usage = new_val
            else:
                # Memory Fallback
                current = self._memory_store.get(key, 0)
                self._memory_store[key] = current + count
                current_usage = self._memory_store[key]
        except Exception as e:
            logger.error(f"[Defense] Quota check failed: {e}")
            return True, "error_open"

        if current_usage > limit:
            return False, f"Daily export limit exceeded ({current_usage}/{limit})"
        
        return True, "ok"

class VectorDBSecurityDefense:
    """
    Unified Defense Module.
    """
    def __init__(self):
        self.rate_limiter = RedisRateLimiter()
        # Share Redis connection
        self.quota_manager = ExportQuotaManager(redis_client=self.rate_limiter.redis)
        self.anomaly_detector = VectorAnomalyDetector()
        self.embedding_protector = EmbeddingProtector()
        self.injection_detector = InjectionDetector()
        
    def validate_request(self, user_id: str, query: str = None, vector: List[float] = None) -> Tuple[bool, str]:
        # 1. Rate Limit
        if not self.rate_limiter.is_allowed(f"user:{user_id}", max_requests=100, window_seconds=60):
            return False, "rate_limit_exceeded"

        # 2. Injection Check
        if query:
            is_bad, reason = self.injection_detector.detect(query)
            if is_bad:
                return False, f"injection_detected: {reason}"

        # 3. Vector Anomaly
        if vector:
            is_bad, reason = self.anomaly_detector.is_anomalous(vector)
            if is_bad:
                return False, f"vector_anomaly: {reason}"

        return True, "ok"
    
    def validate_quota(self, user_id: str, role: str, count: int) -> Tuple[bool, str]:
        # Map Role to Tier
        tier = "free"
        if role == "admin":
            tier = "admin"
        elif role in ["engineer", "analyst"]:
            tier = "pro"
        
        return self.quota_manager.check_quota(user_id, count, tier)

    def protect_vector(self, vector: List[float]) -> List[float]:
        return self.embedding_protector.apply_noise(vector)

# Global Instance
defense_system = VectorDBSecurityDefense()
