# -*- coding: utf-8 -*-
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from llm_backend.server.vector_server.core.security.access_control import (
    AccessControlManager,
    Role,
)
from llm_backend.utils.logger import logger, audit
import os
import hmac
import hashlib
import jwt


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware using BaseHTTPMiddleware pattern.
    This ensures proper interception of all HTTP requests.
    """

    def __init__(self, app, access_manager: AccessControlManager, config=None):
        super().__init__(app)
        logger.info("Security middleware initialized (BaseHTTPMiddleware)")
        self.access_manager = access_manager
        self.config = config

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Intercepts every HTTP request, performs authentication,
        and injects user context into request.state.
        """
        # 0. Bypass for CORS preflight (OPTIONS)
        if request.method == "OPTIONS":
            return await call_next(request)

        # 1. Check for master API key in header (Service Auth)
        x_api_key = request.headers.get("x-api-key")
        master_key = os.getenv("VECTOR_API_KEY")

        # 2. Check for JWT token (User Auth)
        auth_header = request.headers.get("Authorization")

        user_role = Role.VIEWER  # Default
        user_id = "anonymous"
        auth_type = "none"

        # Check API Key First
        if x_api_key and master_key:
            hashed_input = hashlib.sha256(x_api_key.encode()).hexdigest()
            hashed_master = hashlib.sha256(master_key.encode()).hexdigest()

            if hmac.compare_digest(hashed_input, hashed_master):
                user_role = Role.ADMIN
                user_id = "master_admin"
                auth_type = "api_key"
                audit(
                    "Admin access granted via API key",
                    user_id=user_id,
                    action="authenticate",
                    status="success",
                )
                logger.debug("[Middleware] Admin access granted via API key")
            else:
                audit(
                    "Invalid API key attempt", action="authenticate", status="failure"
                )
                logger.warning("!!! API KEY MISMATCH !!!")

        # Then check JWT if not already authenticated as admin
        elif auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Use secret from config or env
                secret = getattr(self.config.security, "jwt_secret", None) or os.getenv(
                    "JWT_SECRET", "change_me_in_production"
                )
                payload = jwt.decode(token, secret, algorithms=["HS256"])
                user_id = payload.get("user_id") or payload.get("sub")
                user_role = Role(payload.get("role", Role.VIEWER))
                user_team = payload.get("team") # Allow team override from JWT
                auth_type = "jwt"
                audit(
                    "User access granted via JWT",
                    user_id=user_id,
                    action="authenticate",
                    status="success",
                )
                logger.debug(
                    f"[Middleware] User access granted via JWT: {user_id} ({user_role})"
                )
            except Exception as e:
                audit(
                    f"JWT validation failed: {e}",
                    action="authenticate",
                    status="failure",
                )
                logger.warning(f"[Middleware] JWT validation failed: {e}")

        # Build user context
        context = {
            "type": "user" if auth_type != "api_key" else "service",
            "user": {
                "id": user_id,
                "role": user_role,
                "team": user_team if 'user_team' in locals() else ("internal" if user_role in [Role.ADMIN, Role.ENGINEER] else "public"),
            },
            "auth_type": auth_type,
            "ip": request.client.host if request.client else "unknown",
        }

        # Inject into request.state
        request.state.user_context = context
        request.state.access_manager = self.access_manager
        request.state.config = self.config

        logger.debug(f"[Middleware] Auth finished: user={user_id}, role={user_role}, type={auth_type}")

        # Continue to next handler
        response = await call_next(request)
        return response
