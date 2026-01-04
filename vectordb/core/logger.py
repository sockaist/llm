import sys
import logging
import json
import contextvars
from datetime import datetime
from typing import Any, Dict

from vectordb.core.config import Config

# Context variable to store correlation ID across async calls
correlation_id_ctx = contextvars.ContextVar("correlation_id", default=None)

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno
        }
        
        # Add correlation ID if present
        cid = correlation_id_ctx.get()
        if cid:
            log_record["correlation_id"] = cid
            
        # Add extra fields usually passed via extra={...}
        if hasattr(record, "props"):
            log_record.update(record.props)

        # Handle exceptions
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': "\033[36m",    # Cyan
        'INFO': "\033[32m",     # Green
        'WARNING': "\033[33m",  # Yellow
        'ERROR': "\033[31m",    # Red
        'CRITICAL': "\033[41m", # Red Background
    }
    TIME_COLOR = "\033[34m"     # Blue
    NAME_COLOR = "\033[90m"     # Gray
    RESET = "\033[0m"

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        cid = correlation_id_ctx.get() or "system"
        
        # [Timestamp] [  Level   ] [Name] (CID) → Message
        colored_line = (
            f"{self.TIME_COLOR}[{timestamp}]{self.RESET} "
            f"{level_color}[{record.levelname:^10}]{self.RESET} "
            f"{self.NAME_COLOR}[{record.name}]{self.RESET} "
            f"({cid}) → {record.getMessage()}"
        )
        return colored_line

def setup_logger(name: str = "vectordb") -> logging.Logger:
    """
    Configure and return a logger instance based on App Config.
    """
    config = Config.load()
    log_level_str = config.logging.level.upper()
    log_format = config.logging.format
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level_str)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
        
    handler = logging.StreamHandler(sys.stdout)
    
    if log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        # Standardize on ColoredFormatter for console
        handler.setFormatter(ColoredFormatter())
        
    logger.addHandler(handler)
    return logger

def get_uvicorn_log_config():
    """Returns a dictionary config for uvicorn to use our ColoredFormatter."""
    config = Config.load()
    level = config.logging.level.upper()
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": ColoredFormatter,
            },
            "access": {
                "()": ColoredFormatter,
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": level},
            "uvicorn.error": {"level": level},
            "uvicorn.access": {"handlers": ["access"], "level": level, "propagate": False},
        },
    }

# Initialize Global Logger
logger = setup_logger()
