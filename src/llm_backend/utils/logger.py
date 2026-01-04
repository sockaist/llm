# src/llm_backend/utils/logger.py
import logging
import os
import sys
import contextvars
import hmac
import hashlib
import getpass
import socket
import platform
import psutil
from pathlib import Path
from threading import Lock
from typing import Optional, Union, Dict, Any
from datetime import datetime, timezone, timedelta

APP_MODE = os.environ.get("APP_MODE", "dev")

# Correlation ID Context
correlation_id_ctx = contextvars.ContextVar("correlation_id", default="system")

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../logs"))
os.makedirs(LOG_DIR, exist_ok=True)

# Clean old logs
try:
    deleted = init_log_folder(LOG_DIR, retention_days=30, key_env="LOG_KEY")
except Exception:
    pass

LOG_FILE = os.path.join(LOG_DIR, f"llm_backend_{datetime.now():%Y%m%d}.log")


# Multi-color Formatter
class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red Background
    }
    TIME_COLOR = "\033[34m"  # Blue
    NAME_COLOR = "\033[90m"  # Gray
    RESET = "\033[0m"

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Get CID from contextvars
        cid = correlation_id_ctx.get()

        # [Timestamp] [  Level   ] [Name] (CID) -> Message
        colored_line = (
            f"{self.TIME_COLOR}[{timestamp}]{self.RESET} "
            f"{level_color}[{record.levelname:^10}]{self.RESET} "
            f"{self.NAME_COLOR}[{record.name}]{self.RESET} "
            f"({cid}) -> {record.getMessage()}"
        )
        return colored_line


formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d -> %(message)s",
    "%Y-%m-%d %H:%M:%S",
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)

logger = logging.getLogger("llm_backend")
logger.setLevel(logging.DEBUG if APP_MODE == "dev" else logging.INFO)
logger.propagate = False

if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# --- Audit Logger ---
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "audit.log")
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False

audit_formatter = logging.Formatter(
    "[AUDIT] [%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S"
)

audit_handler = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
audit_handler.setFormatter(audit_formatter)
if not audit_logger.handlers:
    audit_logger.addHandler(audit_handler)
    # Also log audits to console for visibility in dev
    if APP_MODE == "dev":
        audit_logger.addHandler(console_handler)

# Secure Logger
SECURE_LOG_ENABLE = os.environ.get("SECURE_LOG", "false").lower() == "true"

# Standardize KSS Loggers (both case variants)
for name in ["kss", "Kss"]:
    logger_obj = logging.getLogger(name)
    logger_obj.setLevel(logging.INFO)
    logger_obj.propagate = False
    for h in logger_obj.handlers[:]:
        logger_obj.removeHandler(h)
    
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(ColoredFormatter())
    logger_obj.addHandler(h)

# Protect against root logger pollution (Uvicorn/Libraries)
root = logging.getLogger()
for h in root.handlers[:]:
    if isinstance(h, logging.StreamHandler):
        # Only remove if it's not our intended handler
        root.removeHandler(h)

# Add a single controlled root handler if needed, or keep it clean
# For now, we rely on individual loggers (llm_backend, vectordb, kss)

# -----------------------------------------------------------------------------
# Secure Logging & Log Integrity (Consolidated from secure_logger.py)
# -----------------------------------------------------------------------------

def _get_key_from_env(env_name: str):
    key = os.environ.get(env_name)
    if not key:
        return b"default_secret_key_change_me" # Fallback for dev
    return key.encode("utf-8")

def compute_hmac(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def init_log_folder(log_dir: str, retention_days: int = 30):
    p = Path(log_dir)
    p.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = []
    for f in p.iterdir():
        try:
            if not f.is_file(): continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime, timezone.utc)
            if mtime < cutoff:
                f.unlink()
                deleted.append(f.name)
        except Exception: continue
    return deleted

class SecureJSONFileHandler(logging.Handler):
    def __init__(self, filepath: str, app_name: str = "app", key_env: str = "LOG_KEY"):
        super().__init__()
        self.filepath = Path(filepath)
        self.app_name = app_name
        self._key = _get_key_from_env(key_env)
        self._lock = Lock()
        self._file = open(self.filepath, "ab")
        if self._file.tell() == 0:
            self._write_header()
        self._chain_hash = None

    def _write_header(self):
        meta = {
            "app": self.app_name,
            "host": socket.gethostname(),
            "start_time": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
        }
        line = (json.dumps({"_header": meta}) + "\n").encode("utf-8")
        with self._lock:
            self._file.write(line)
            self._file.flush()
            self._chain_hash = compute_sha256(line)

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            entry = {"ts": datetime.now(timezone.utc).isoformat(), "level": record.levelname, "msg": msg}
            entry_json = json.dumps(entry, sort_keys=True)
            prev = self._chain_hash or ""
            chain_input = (prev + "|" + entry_json).encode("utf-8")
            current_hash = compute_sha256(chain_input)
            hmac_val = compute_hmac(self._key, chain_input)
            
            out = {"entry": entry, "_chain_hash": current_hash, "_hmac": hmac_val}
            line = (json.dumps(out) + "\n").encode("utf-8")
            with self._lock:
                self._file.write(line)
                self._file.flush()
                self._chain_hash = current_hash
        except Exception:
            self.handleError(record)

    def close(self):
        if hasattr(self, '_file') and not self._file.closed:
            self._file.close()
        super().close()

# --- Audit & Helper Functions ---

def audit(msg, user_id="system", resource="none", action="none", status="success"):
    """상세 감사 로그 기록."""
    audit_logger.info(
        f"User:{user_id} | Action:{action} | Resource:{resource} | Status:{status} | Message:{msg}"
    )

def info(msg): logger.info(msg)
def debug(msg): logger.debug(msg)
def warn(msg): logger.warning(msg)
def error(msg): logger.error(msg)
def critical(msg): logger.critical(msg)

if SECURE_LOG_ENABLE:
    secure_path = os.path.join(LOG_DIR, f"secure_{datetime.now():%Y%m%d}.jsonl")
    try:
        secure_handler = SecureJSONFileHandler(
            secure_path, app_name="llm_backend", key_env="LOG_KEY"
        )
        logger.addHandler(secure_handler)
        logger.info("[SecureLogger] initialized successfully.")
    except Exception as e:
        logger.error(f"[SecureLogger] initialization failed: {e}")
