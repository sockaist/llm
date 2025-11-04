# src/llm_backend/utils/logger.py
import logging
import os
from datetime import datetime
from llm_backend.utils.secure_logger import SecureJSONFileHandler, init_log_folder

APP_MODE = os.environ.get("APP_MODE", "dev")

LOG_DIR = os.path.join(os.path.dirname(__file__), "../../logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 🔍 오래된 로그 삭제
try:
    deleted = init_log_folder(LOG_DIR, retention_days=30, key_env="LOG_KEY")
    if deleted:
        print(f"[logger] Cleaned old log files: {len(deleted)}")
except Exception as e:
    print(f"[logger] Failed to clean old logs: {e}")

LOG_FILE = os.path.join(LOG_DIR, f"llm_backend_{datetime.now():%Y%m%d}.log")

formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d → %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)

logger = logging.getLogger("llm_backend")
logger.setLevel(logging.DEBUG if APP_MODE == "dev" else logging.INFO)

if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# Secure Logger 추가
SECURE_LOG_ENABLE = os.environ.get("SECURE_LOG", "false").lower() == "true"

if SECURE_LOG_ENABLE:
    secure_path = os.path.join(LOG_DIR, f"secure_{datetime.now():%Y%m%d}.jsonl")
    try:
        secure_handler = SecureJSONFileHandler(secure_path, app_name="llm_backend", key_env="LOG_KEY")
        logger.addHandler(secure_handler)
        logger.info("[SecureLogger] initialized successfully.")
    except Exception as e:
        logger.error(f"[SecureLogger] initialization failed: {e}")

# 편의 함수들
def info(msg): logger.info(msg)
def debug(msg): logger.debug(msg)
def warn(msg): logger.warning(msg)
def error(msg): logger.error(msg)
def critical(msg): logger.critical(msg)