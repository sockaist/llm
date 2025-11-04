# src/llm_backend/utils/secure_logger.py
import os
import json
import time
import hmac
import hashlib
import getpass
import socket
import platform
import psutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
import logging
from logging import Handler, LogRecord
from threading import Lock
from typing import Optional

# ---------------------------
# 유틸: HMAC / 해시
# ---------------------------
def _get_key_from_env(env_name: str):
    key = os.environ.get(env_name)
    if not key:
        raise RuntimeError(f"Log integrity key not found in env '{env_name}'")
    return key.encode("utf-8")

def compute_hmac(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

# ---------------------------
# 로그 폴더 초기화 + 오래된 파일 삭제
# ---------------------------
def init_log_folder(log_dir: str, retention_days: int = 30, key_env: str = "LOG_KEY"):
    p = Path(log_dir)
    p.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    deleted = []
    for f in p.iterdir():
        try:
            if not f.is_file():
                continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime, timezone.utc)
            if mtime < cutoff:
                f.unlink()
                deleted.append(f.name)
        except Exception:
            logging.getLogger(__name__).warning(f"Failed to delete old log: {f}")
            continue

    if deleted:
        logging.getLogger(__name__).info(f"[SecureLogger] Cleaned {len(deleted)} old log files.")
    return deleted

# ---------------------------
# 커스텀 핸들러 (JSONL, chain hash)
# ---------------------------
class SecureJSONFileHandler(Handler):
    def __init__(self, filepath: str, app_name: str = "app", key_env: str = "LOG_KEY", mode="a", encoding="utf-8"):
        super().__init__()
        self.filepath = Path(filepath)
        self.app_name = app_name
        self.mode = mode
        self.encoding = encoding
        self._lock = Lock()
        self._key_env = key_env
        self._key = _get_key_from_env(key_env)
        self._file = open(self.filepath, mode + "b")
        self._file.seek(0, os.SEEK_END)
        self._chain_hash = None

        if self._file.tell() == 0:
            self._write_header()
        else:
            self._recover_chain_hash()

    def _get_system_info(self):
        """시스템 환경 정보 수집"""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat()
            cpu_count = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else None
            mem = psutil.virtual_memory()
            venv = os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_DEFAULT_ENV") or None
            return {
                "boot_time": boot_time,
                "cpu_count": cpu_count,
                "cpu_freq_mhz": round(cpu_freq, 1) if cpu_freq else None,
                "memory_gb": round(mem.total / (1024 ** 3), 2),
                "venv": venv,
            }
        except Exception as e:
            return {"error": f"system_info_error: {e}"}

    def _write_header(self):
        meta = {
            "app": self.app_name,
            "host": socket.gethostname(),
            "user": getpass.getuser(),
            "start_time": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "pid": os.getpid(),
            **self._get_system_info(),  # ✅ 시스템 정보 병합
        }

        meta_bytes = json.dumps({"_header": meta}, ensure_ascii=False).encode(self.encoding)
        header_hmac = compute_hmac(self._key, meta_bytes)
        header_record = {"_header": meta, "_header_hmac": header_hmac}
        line = (json.dumps(header_record, ensure_ascii=False) + "\n").encode(self.encoding)
        with self._lock:
            self._file.write(line)
            self._file.flush()
            os.fsync(self._file.fileno())
            self._chain_hash = compute_sha256(line)

    def _recover_chain_hash(self):
        with self._lock:
            try:
                self._file.flush()
                size = self._file.tell()
                read_bytes = min(size, 16 * 1024)
                self._file.seek(-read_bytes, os.SEEK_END)
                chunk = self._file.read(read_bytes)
            except OSError:
                self._file.seek(0)
                chunk = self._file.read()
        try:
            text = chunk.decode(self.encoding, errors="ignore")
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if not lines:
                self._chain_hash = None
                return
            last = json.loads(lines[-1])
            self._chain_hash = last.get("_chain_hash") or compute_sha256(lines[-1].encode(self.encoding))
        except Exception:
            self._chain_hash = None

    def emit(self, record: LogRecord):
        try:
            msg = self.format(record)
            ts = datetime.now(timezone.utc).isoformat()
            rec = {
                "ts": ts,
                "level": record.levelname,
                "msg": msg,
                "logger": record.name,
                "pathname": record.pathname,
                "lineno": record.lineno,
                "process": record.process,
                "thread": record.threadName
            }
            rec_json = json.dumps(rec, ensure_ascii=False, sort_keys=True)
            prev = self._chain_hash or ""
            chain_input = (prev + "|" + rec_json).encode(self.encoding)
            chain_hash = compute_sha256(chain_input)
            line_hmac = compute_hmac(self._key, chain_input)

            out = {"entry": rec, "_chain_hash": chain_hash, "_line_hmac": line_hmac}
            out_line = (json.dumps(out, ensure_ascii=False) + "\n").encode(self.encoding)

            with self._lock:
                self._file.write(out_line)
                self._file.flush()
                os.fsync(self._file.fileno())
                self._chain_hash = chain_hash
        except Exception:
            self.handleError(record)

    def close(self):
        try:
            if not self._file.closed:
                self._file.close()
        finally:
            super().close()

# ---------------------------
# 로그 검증
# ---------------------------
def verify_log_file(path: str, key: Optional[bytes] = None, key_env: str = "LOG_KEY"):
    key_bytes = key if key is not None else _get_key_from_env(key_env)
    problems = []
    try:
        with open(path, "rb") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        if not lines:
            return False, ["empty file"]

        header_record = json.loads(lines[0].decode("utf-8"))
        header_meta = header_record.get("_header")
        header_hmac = header_record.get("_header_hmac")
        if compute_hmac(key_bytes, json.dumps({"_header": header_meta}, ensure_ascii=False).encode("utf-8")) != header_hmac:
            problems.append("header_hmac_mismatch")

        prev_chain = compute_sha256((lines[0] + b"\n"))
        for i, raw in enumerate(lines[1:], start=1):
            try:
                rec = json.loads(raw.decode("utf-8"))
                stored_chain = rec.get("_chain_hash")
                stored_line_hmac = rec.get("_line_hmac")
                entry = rec.get("entry")
                rec_json = json.dumps(entry, ensure_ascii=False, sort_keys=True)
                chain_input = (prev_chain + "|" + rec_json).encode("utf-8")
                expected_chain = compute_sha256(chain_input)
                expected_hmac = compute_hmac(key_bytes, chain_input)
                if expected_chain != stored_chain:
                    problems.append(f"chain_mismatch_line_{i}")
                if expected_hmac != stored_line_hmac:
                    problems.append(f"line_hmac_mismatch_line_{i}")
                prev_chain = stored_chain
            except Exception:
                problems.append(f"line_parse_error_{i}")
    except Exception as e:
        return False, [f"file_read_error: {e}"]

    return len(problems) == 0, problems