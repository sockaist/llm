# -*- coding: utf-8 -*-
import os
import hashlib
import hmac
from fastapi import Header, HTTPException, status
from llm_backend.utils.logger import logger

# ============================================================
# API Key 기반 인증 (보안 강화 버전)
# ============================================================

# 원본 키를 환경 변수에서 불러옴 (한 번만)
_RAW_API_KEY = os.getenv("VECTOR_API_KEY")

if not _RAW_API_KEY:
    logger.warning("[Auth] VECTOR_API_KEY not set — using development key.")
    _RAW_API_KEY = "dev-key"

# SHA-256으로 해시 (원본은 즉시 제거)
_HASHED_API_KEY = hashlib.sha256(_RAW_API_KEY.encode()).hexdigest()
del _RAW_API_KEY  # 메모리에서 원본 제거

logger.info("[Auth] API key hash initialized and secured.")


# ------------------------------------------------------------
# 헤더 검증 함수
# ------------------------------------------------------------
async def verify_api_key(x_api_key: str = Header(...)):
    """
    헤더의 'x-api-key' 값의 SHA-256 해시가 서버 내부 해시와 일치하는지 검증합니다.
    원본 키는 메모리에 저장하지 않고 해시만 비교합니다.
    """
    if not x_api_key:
        logger.warning("[Auth] Missing x-api-key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key in header."
        )

    # 헤더 입력값도 해시 처리
    hashed_input = hashlib.sha256(x_api_key.encode()).hexdigest()

    # 안전한 비교 (timing attack 방지)
    if not hmac.compare_digest(hashed_input, _HASHED_API_KEY):
        logger.warning(f"[Auth] Invalid API key attempt (hash={hashed_input[:12]}...)")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Invalid API key."
        )

    logger.debug("[Auth] API key verified successfully")
    return True

# ------------------------------------------------------------
# Multi-Tenancy Context Injection
# ------------------------------------------------------------
from fastapi import Request

async def get_user_context(request: Request) -> dict:
    """
    Retrieves the User Context populated by SecurityMiddleware.
    """
    # If middleware didn't run (e.g. tests without middleware), fallback
    if hasattr(request.state, "user_context"):
        return request.state.user_context
    
    # Fallback for direct testing or if middleware missing
    return {
        "user": {
            "id": request.headers.get("X-User-ID", "anonymous"),
            "role": request.headers.get("X-Role", "viewer"),
            "team": "public"
        },
        "ip": request.client.host if request.client else "unknown"
    }