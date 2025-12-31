# src/llm_backend/utils/logger.py
import logging
import os
from datetime import datetime
from llm_backend.utils.secure_logger import SecureJSONFileHandler, init_log_folder

APP_MODE = os.environ.get("APP_MODE", "dev")

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
        
        # [Timestamp] [  Level   ] Name:Line -> Message
        colored_line = (
            f"{self.TIME_COLOR}[{timestamp}]{self.RESET} "
            f"{level_color}[{record.levelname:^10}]{self.RESET} "
            f"{self.NAME_COLOR}{record.name}:{record.lineno:<4}{self.RESET} "
            f"→ {record.getMessage()}"
        )
        return colored_line

formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s:%(lineno)d → %(message)s",
    "%Y-%m-%d %H:%M:%S"
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

# Secure Logger
SECURE_LOG_ENABLE = os.environ.get("SECURE_LOG", "false").lower() == "true"

# Suppress KSS Logger
logging.getLogger("kss").setLevel(logging.WARNING)

if SECURE_LOG_ENABLE:
    secure_path = os.path.join(LOG_DIR, f"secure_{datetime.now():%Y%m%d}.jsonl")
    try:
        secure_handler = SecureJSONFileHandler(secure_path, app_name="llm_backend", key_env="LOG_KEY")
        logger.addHandler(secure_handler)
        logger.info("[SecureLogger] initialized successfully.")
    except Exception as e:
        logger.error(f"[SecureLogger] initialization failed: {e}")

# Convenience functions
def info(msg): logger.info(msg)
def debug(msg): logger.debug(msg)
def warn(msg): logger.warning(msg)
def error(msg): logger.error(msg)
def critical(msg): logger.critical(msg)