# -*- coding: utf-8 -*-
"""
Standardized Error Handling for VortexDB API.
Provides consistent error responses across all endpoints.
"""

from enum import Enum
from typing import Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import traceback
import os

from llm_backend.utils.logger import logger


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    # Authentication & Authorization (1xxx)
    UNAUTHORIZED = "E1001"
    FORBIDDEN = "E1002"
    INVALID_API_KEY = "E1003"
    TOKEN_EXPIRED = "E1004"

    # Validation Errors (2xxx)
    INVALID_REQUEST = "E2001"
    MISSING_FIELD = "E2002"
    INVALID_FORMAT = "E2003"
    VALUE_OUT_OF_RANGE = "E2004"

    # Resource Errors (3xxx)
    NOT_FOUND = "E3001"
    COLLECTION_NOT_FOUND = "E3002"
    DOCUMENT_NOT_FOUND = "E3003"
    ALREADY_EXISTS = "E3004"

    # Rate Limiting & Quota (4xxx)
    RATE_LIMITED = "E4001"
    QUOTA_EXCEEDED = "E4002"

    # Security Errors (5xxx)
    INJECTION_DETECTED = "E5001"
    ANOMALY_DETECTED = "E5002"
    ACCESS_DENIED = "E5003"

    # Server Errors (9xxx)
    INTERNAL_ERROR = "E9001"
    SERVICE_UNAVAILABLE = "E9002"
    DEPENDENCY_FAILURE = "E9003"


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    status: str = "error"
    code: str
    message: str
    detail: Optional[str] = None
    request_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "code": "E2001",
                "message": "Invalid request parameters",
                "detail": "top_k must be between 1 and 100",
                "request_id": "req_abc123",
            }
        }


class APIError(HTTPException):
    """Custom API exception with error code support."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        detail: Optional[str] = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.error_detail = detail
        super().__init__(status_code=status_code, detail=message)


# Error code to HTTP status mapping
ERROR_STATUS_MAP = {
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.INVALID_API_KEY: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.MISSING_FIELD: 400,
    ErrorCode.INVALID_FORMAT: 400,
    ErrorCode.VALUE_OUT_OF_RANGE: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.COLLECTION_NOT_FOUND: 404,
    ErrorCode.DOCUMENT_NOT_FOUND: 404,
    ErrorCode.ALREADY_EXISTS: 409,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.QUOTA_EXCEEDED: 429,
    ErrorCode.INJECTION_DETECTED: 400,
    ErrorCode.ANOMALY_DETECTED: 400,
    ErrorCode.ACCESS_DENIED: 403,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.DEPENDENCY_FAILURE: 502,
}


def raise_api_error(
    code: ErrorCode, message: str, detail: Optional[str] = None
) -> None:
    """Raise a standardized API error."""
    status_code = ERROR_STATUS_MAP.get(code, 400)
    raise APIError(code=code, message=message, detail=detail, status_code=status_code)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handler for APIError exceptions."""
    request_id = getattr(request.state, "request_id", None)

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code.value,
            message=exc.message,
            detail=exc.error_detail,
            request_id=request_id,
        ).model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions."""
    request_id = getattr(request.state, "request_id", None)
    is_debug = os.getenv("VECTORDB_DEBUG", "0") == "1"

    # Log the full error
    logger.error(
        f"[Exception] {request.method} {request.url} -> {exc}\n{traceback.format_exc()}"
    )

    # Show stack trace only in debug mode
    detail = traceback.format_exc() if is_debug else None

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR.value,
            message="An internal error occurred",
            detail=detail,
            request_id=request_id,
        ).model_dump(),
    )


def register_error_handlers(app):
    """Register all error handlers with the FastAPI app."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
