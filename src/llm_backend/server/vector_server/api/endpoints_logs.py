# -*- coding: utf-8 -*-
import os
from fastapi import APIRouter, HTTPException, Query, Depends, Header
from typing import List, Optional
from pydantic import BaseModel

from llm_backend.utils.logger import logger, LOG_DIR
from llm_backend.server.vector_server.core.auth import verify_api_key
from llm_backend.server.vector_server.api.endpoints_admin import _check_admin_secret

router = APIRouter(
    prefix="/logs", tags=["Logs & Audit"], dependencies=[Depends(verify_api_key)]
)


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    raw: str


class LogResponse(BaseModel):
    lines: List[str]
    total_read: int
    has_more: bool


@router.get("/system", response_model=LogResponse)
async def get_system_logs(
    lines: int = Query(100, ge=1, le=1000),
    level: Optional[str] = None,
    keyword: Optional[str] = None,
    x_admin_secret: Optional[str] = Header(None),
):
    """
    Retrieve the latest N lines from the system log file.
    Supports filtering by level (INFO, ERROR) or keyword.
    Requires Admin Secret.
    """
    _check_admin_secret(x_admin_secret)

    log_file = os.path.join(LOG_DIR, "llm_backend.log")  # Assuming standard name
    # If rotating handler adds date, we might need a robust finder.
    # Let's try to find the latest log file.

    if not os.path.exists(log_file):
        # Fallback to finding latest .log in dir
        try:
            candidates = sorted([f for f in os.listdir(LOG_DIR) if f.endswith(".log")])
            if candidates:
                log_file = os.path.join(LOG_DIR, candidates[-1])
            else:
                return LogResponse(
                    lines=["No log file found."], total_read=0, has_more=False
                )
        except Exception:
            return LogResponse(
                lines=["Log directory inaccessible."], total_read=0, has_more=False
            )

    try:
        # Read file in reverse is expensive for large files without specialized blocks.
        # We'll use a simple readlines() for now if file isn't huge, or `deque` for last N lines.

        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            # Simple approach: read all, filter, take last N
            # For production, utilize `tail` approach with seek.
            all_lines = f.readlines()

        # Reverse to show newest first
        all_lines.reverse()

        filtered_lines = []
        for line in all_lines:
            line = line.strip()
            if not line:
                continue

            # Application-level filtering
            if level and f"[{level.upper()}" not in line:
                continue
            if keyword and keyword.lower() not in line.lower():
                continue

            filtered_lines.append(line)
            if len(filtered_lines) >= lines:
                break

        return LogResponse(
            lines=filtered_lines,
            total_read=len(filtered_lines),
            has_more=len(all_lines) > len(filtered_lines),
        )

    except Exception as e:
        logger.error(f"[API:/logs/system] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit", response_model=LogResponse)
async def get_audit_logs(
    lines: int = Query(50, ge=1, le=500), x_admin_secret: Optional[str] = Header(None)
):
    """
    Retrieve only Audit-related log entries (tagged with [Audit] or critical actions).
    """
    # Reuse the logic with a forced keyword or specialized parser
    return await get_system_logs(
        lines=lines, keyword="[Audit]", x_admin_secret=x_admin_secret
    )
