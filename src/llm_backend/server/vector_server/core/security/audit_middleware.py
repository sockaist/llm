# -*- coding: utf-8 -*-
import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from llm_backend.utils.logger import logger, audit, correlation_id_ctx

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle Correlation IDs and automatic Audit Logging for mutations.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Set Correlation ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        token = correlation_id_ctx.set(request_id)
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 2. Audit Mutation Requests (POST, PUT, DELETE, PATCH)
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                user_context = getattr(request.state, "user_context", {})
                user_id = user_context.get("user", {}).get("id", "anonymous")
                
                # Exclude health checks/metrics from auto-audit if they use POST
                if not any(x in request.url.path for x in ["/health", "/metrics", "/logs"]):
                    status = "success" if response.status_code < 400 else "failure"
                    audit(
                        msg=f"Request Performance: {process_time:.3f}s",
                        user_id=user_id,
                        resource=request.url.path,
                        action=request.method,
                        status=status
                    )
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            # Audit catastrophic failures
            user_context = getattr(request.state, "user_context", {})
            user_id = user_context.get("user", {}).get("id", "anonymous")
            audit(
                msg=f"Request failed with exception: {str(e)}",
                user_id=user_id,
                resource=request.url.path,
                action=request.method,
                status="error"
            )
            raise e
        finally:
            correlation_id_ctx.reset(token)
