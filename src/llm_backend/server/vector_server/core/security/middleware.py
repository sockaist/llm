# -*- coding: utf-8 -*-
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from llm_backend.server.vector_server.core.security.access_control import AccessControlManager, Role
from llm_backend.server.vector_server.core.security.defense import defense_system
from llm_backend.server.vector_server.core.security.audit_logger import audit_logger
from llm_backend.server.vector_server.config.security_config import VectorDBConfig
from llm_backend.utils.logger import logger
import time

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for Global Security Policies:
    1. Context Extraction (Identity)
    2. Rate Limiting (Defense Layer 1)
    3. Audit Logging (Request Start - Optional or end)
    """
    def __init__(self, app, access_manager: AccessControlManager, config: VectorDBConfig = None):
        super().__init__(app)
        self.access_manager = access_manager
        self.config = config

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 0. Global Kill Switch check (if needed) or Feature Toggles
        auth_enabled = True
        if self.config and not self.config.security.authentication.enabled:
            auth_enabled = False
            
        rate_limit_enabled = True
        if self.config and not self.config.security.rate_limiting.enabled:
             rate_limit_enabled = False

        # 1. Extract Identity Context
        # If Auth Disabled (Tier 0), verify localhost restriction? 
        # (Assuming bind_address handled at uvicorn level, but we can check here too)
        
        user_id = request.headers.get("X-User-ID", "anonymous")
        user_role = request.headers.get("X-User-Role", Role.VIEWER)
        
        if not auth_enabled:
             # Force anonymous/admin context for Dev?
             # User specified Tier 0 dev warnings: "All users have admin access"
             # So if Tier 0, we might default to ADMIN or leave as is but skip checks later?
             # Better: Set context as "Dev Admin" if dev mode.
             if self.config and self.config.security.tier == 0:
                 user_role = Role.ADMIN
                 user_id = "dev_user"
        
        user_team = request.headers.get("X-User-Team", "public")
        service_id = request.headers.get("X-Service-ID")
        
        # Build Context
        context = {
            "user": {
                "id": user_id,
                "role": user_role,
                "team": user_team
            },
            "service_id": service_id,
            "ip": request.client.host,
            "path": request.url.path,
            "method": request.method,
            "timestamp": start_time,
            # Pass config tier to endpoints if needed
            "security_tier": self.config.security.tier if self.config else 1
        }
        
        # Inject into Request State for Endpoints
        request.state.user_context = context
        request.state.access_manager = self.access_manager
        request.state.config = self.config # Pass config down

        # 2. Rate Limiting (Global Defense)
        if rate_limit_enabled and not service_id:
            # Check Rate Limit based on IP or UserID
            # Enhanced: Use config limits if available? 
            # For now keep existing logic but wrapped in toggle.
            limit_key = f"user:{user_id}" if user_id != "anonymous" else f"ip:{request.client.host}"
            if not defense_system.rate_limiter.is_allowed(limit_key, max_requests=100, window_seconds=60):
                await audit_logger.log_event("rate_limit_exceeded", {
                    "user_id": user_id,
                    "ip": request.client.host,
                    "path": request.url.path
                })
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests", "error": "rate_limit_exceeded"}
                )

        # 3. Process Request
        try:
            response = await call_next(request)
            
            # Simple Audit for Non-GET/Search calls (Optional global logging)
            # Tier 2 Logic for API Access
            # if request.method not in ["GET", "OPTIONS"]:
            #     await audit_logger.log_event("api_access", {
            #         "user": user_id, 
            #         "path": request.url.path, 
            #         "status": response.status_code
            #     })
                
            return response
            
        except Exception as exc:
            logger.error(f"[Middleware] Uncaught Exception: {exc}")
            # Log 500 errors
            await audit_logger.log_event("server_error", {
                 "user": user_id,
                 "path": request.url.path,
                 "error": str(exc)
            })
            raise exc
