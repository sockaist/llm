# -*- coding: utf-8 -*-
import asyncio
import json
import os
import time
import datetime
from typing import Dict, Any, List
import hashlib
from llm_backend.utils.logger import logger

# Constants for Event Categorization
TIER1_EVENTS = {
    "user_login_failed",
    "user_login_success",
    "access_denied",
    "privilege_escalation",
    "data_delete",
    "collection_deleted",
    "bulk_export",
    "config_changed",
    "role_changed",
    "brute_force_detected",
    "injection_detected",
    "service_auth_failed",
}

LOG_DIR = "logs/audit"
CRITICAL_LOG_FILE = os.path.join(LOG_DIR, "audit_critical.jsonl")
HOT_LOG_FILE = os.path.join(LOG_DIR, "audit_hot.jsonl")

# Ensure Log Directory Exists
os.makedirs(LOG_DIR, exist_ok=True)

# Chain State File

CHAIN_STATE_FILE = os.path.join(LOG_DIR, "audit_chain.state")


class ProductionAuditLogger:
    """
    Tiered Audit Logger System with Hash Chaining for Integrity.
    """

    def __init__(self, batch_size: int = 1000, flush_interval: float = 1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.log_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._running = False
        self._worker_task = None

        # Load Chain State (for Integrity)
        self.critical_hash = "0" * 64
        self.hot_hash = "0" * 64
        self._load_chain_state()

        # Lock for chain state updates (Thread safety if needed, here asyncio single threaded usually)
        # But we might need robust file locking for state file in multi-worker setup.
        # For this MVP single-process server:
        self._state_lock = asyncio.Lock()

        # Start background worker for Tier 2 logs
        self.start()

    def _load_chain_state(self):
        if os.path.exists(CHAIN_STATE_FILE):
            try:
                with open(CHAIN_STATE_FILE, "r") as f:
                    state = json.load(f)
                    self.critical_hash = state.get("critical", self.critical_hash)
                    self.hot_hash = state.get("hot", self.hot_hash)
            except Exception as e:
                logger.error(f"[AuditLogger] Failed to load chain state: {e}")

    def _save_chain_state(self):
        # In a real high-throughput system, we wouldn't write this state file on every log.
        # We might write it periodically or on shutdown.
        # But for correctness, we should persist. Let's do it on every sync write and batch flush.
        try:
            with open(CHAIN_STATE_FILE, "w") as f:
                json.dump(
                    {
                        "critical": self.critical_hash,
                        "hot": self.hot_hash,
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                    },
                    f,
                )
        except Exception as e:
            logger.error(f"[AuditLogger] Failed to save chain state: {e}")

    def _compute_hash(self, prev_hash: str, entry: Dict[str, Any]) -> str:
        # Canonical JSON string
        serialized = json.dumps(entry, sort_keys=True)
        return hashlib.sha256((prev_hash + serialized).encode("utf-8")).hexdigest()

    # ... (start/shutdown same) ...
    def start(self):
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop:
                self._worker_task = loop.create_task(self._batch_worker())
                logger.info("[AuditLogger] Background worker started")

    async def shutdown(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        await self._flush_remaining()
        logger.info("[AuditLogger] Shutdown complete")

    async def log_event(self, event_type: str, event_data: Dict[str, Any]):
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "data": event_data,
        }

        if not event_type:
            return

        if event_type in TIER1_EVENTS:
            self._log_tier1_sync(log_entry)
        else:
            try:
                self.log_queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                logger.warning(
                    "[AuditLogger] Queue full! Fallback to Sync Write (Hot Chain)."
                )
                self._log_hot_sync_fallback(log_entry)

    def _log_tier1_sync(self, entry: Dict[str, Any]):
        """
        Sync write for Critical Events with Hash Chaining.
        """
        try:
            # Update Chain
            entry["prev_hash"] = self.critical_hash
            new_hash = self._compute_hash(self.critical_hash, entry)
            entry["hash"] = new_hash
            self.critical_hash = new_hash

            self._write_to_file(CRITICAL_LOG_FILE, entry)
            self._save_chain_state()

        except Exception as e:
            logger.critical(f"[AuditLogger] TIER 1 WRITE FAILED: {e}")

    def _log_hot_sync_fallback(self, entry: Dict[str, Any]):
        # Fallback writes to Hot Chain
        try:
            entry["prev_hash"] = self.hot_hash
            new_hash = self._compute_hash(self.hot_hash, entry)
            entry["hash"] = new_hash
            self.hot_hash = new_hash

            self._write_to_file(HOT_LOG_FILE, entry)
            self._save_chain_state()
        except Exception:
            pass

    def _write_to_file(self, filepath: str, entry: Dict[str, Any]):
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    async def _batch_worker(self):
        batch = []
        last_flush = time.time()

        while self._running:
            try:
                try:
                    entry = await asyncio.wait_for(
                        self.log_queue.get(), timeout=self.flush_interval
                    )
                    batch.append(entry)
                except asyncio.TimeoutError:
                    pass

                current_time = time.time()
                is_batch_full = len(batch) >= self.batch_size
                is_time_up = (current_time - last_flush) >= self.flush_interval

                if (batch and is_time_up) or is_batch_full:
                    # Flush with chaining
                    await self._flush_batch_chained(batch)
                    batch = []
                    last_flush = current_time

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AuditLogger] Worker error: {e}")
                await asyncio.sleep(1)

    async def _flush_batch_chained(self, batch: List[Dict[str, Any]]):
        """
        Chain and flush batch to hot log.
        """
        if not batch:
            return

        # Prepare batch with hashes
        for entry in batch:
            entry["prev_hash"] = self.hot_hash
            new_hash = self._compute_hash(self.hot_hash, entry)
            entry["hash"] = new_hash
            self.hot_hash = new_hash

        self._save_chain_state()

        try:
            # Run file I/O in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._write_batch_to_file, HOT_LOG_FILE, batch
            )
        except Exception as e:
            logger.error(f"[AuditLogger] Batch flush failed: {e}")
            # Already chained, just retry usage logic or drop (tier 2)
            # If we fail to write, our in-memory hash is ahead of disk.
            # This desyncs the chain. In prod, we'd need better recovery.
            # For now, MVP: Log error.

    def _write_batch_to_file(self, filepath: str, batch: List[Dict[str, Any]]):
        with open(filepath, "a", encoding="utf-8") as f:
            for entry in batch:
                f.write(json.dumps(entry) + "\n")

    async def _flush_remaining(self):
        batch = []
        while not self.log_queue.empty():
            batch.append(self.log_queue.get_nowait())
        if batch:
            await self._flush_batch_chained(batch)


# Global Instance
audit_logger = ProductionAuditLogger()
