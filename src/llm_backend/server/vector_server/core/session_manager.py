# -*- coding: utf-8 -*-
import threading

import uuid
from typing import Dict, Optional
from llm_backend.utils.logger import logger
from llm_backend.server.vector_server.core.resource_pool import _global_pool
from llm_backend.server.vector_server.core.resource_pool import get_vector_manager

# ============================================================
# Session Manager
# ============================================================

class SessionManager:
    """
    세션별 VectorDBManager를 관리.
    - 각 요청에 대해 session_id를 발급하고, 동일 세션 요청은 같은 Manager 사용.
    - 세션이 종료되면 리소스를 풀에 반환.
    """

    def __init__(self):
        self.sessions: Dict[str, object] = {}
        self.lock = threading.Lock()

    # --------------------------------------------------------
    def create_session(self) -> str:
        """새로운 세션 ID를 생성하고 VectorDBManager를 할당."""
        with self.lock:
            session_id = str(uuid.uuid4())
            mgr = get_vector_manager()
            self.sessions[session_id] = mgr
            logger.info(f"[Session] Created new session: {session_id[:8]}")
            return session_id

    # --------------------------------------------------------
    def get_manager(self, session_id: str):
        """기존 세션의 VectorDBManager를 반환."""
        mgr = self.sessions.get(session_id)
        if mgr:
            logger.debug(f"[Session] Reusing manager for session {session_id[:8]}")
            return mgr
        logger.warning(f"[Session] Session not found: {session_id}")
        return None

    # --------------------------------------------------------
    def close_session(self, session_id: str):
        with self.lock:
            mgr = self.sessions.pop(session_id, None)
            if mgr and _global_pool:
                _global_pool.release(mgr)

    # --------------------------------------------------------
    def list_sessions(self) -> list[str]:
        """현재 활성 세션 목록 반환."""
        return list(self.sessions.keys())


# ------------------------------------------------------------
# 전역 인스턴스 (싱글톤)
# ------------------------------------------------------------
_global_session_manager: Optional[SessionManager] = None
_lock = threading.Lock()

def get_session_manager() -> SessionManager:
    global _global_session_manager
    with _lock:
        if _global_session_manager is None:
            _global_session_manager = SessionManager()
            logger.info("[SessionManager] Initialized")
    return _global_session_manager