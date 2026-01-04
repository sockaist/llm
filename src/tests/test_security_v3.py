import json
import os
import shutil
import hashlib

from llm_backend.server.vector_server.core.security.data_filter import (
    SensitiveDataFilter,
    MetadataValidator,
)
from llm_backend.server.vector_server.core.security.defense import ExportQuotaManager
from llm_backend.server.vector_server.core.security.audit_logger import (
    ProductionAuditLogger,
)


# ==========================================
# 0. Test Metadata Validator (API18-Task4)
# ==========================================
class TestMetadataValidation:
    def test_reserved_fields(self):
        # Valid input
        valid, msg = MetadataValidator.validate_input(
            {"title": "Doc A", "author": "bob"}
        )
        assert valid is True

        # Invalid input (Top level)
        invalid_1, msg = MetadataValidator.validate_input(
            {"tenant_id": "other", "vector": []}
        )
        assert valid is True  # Wait, re-check logic.
        # Logic: for key in data.keys(): if key in RESERVED...
        # tenant_id IS reserved.

        invalid_1, msg = MetadataValidator.validate_input({"tenant_id": "other"})
        assert invalid_1 is False
        assert "Reserved field" in msg

        # Invalid input (Nested metadata)
        invalid_2, msg = MetadataValidator.validate_input(
            {"vector": [], "metadata": {"role": "admin"}}
        )
        assert invalid_2 is False
        assert "Reserved field" in msg


# ==========================================
# 1. Test Sensitive Data Filtering (API3)
# ==========================================
class TestSensitiveDataFilter:
    def test_pii_scrubbing_guest(self):
        payload = {
            "id": "123",
            "metadata": {
                "user": "alice",
                "ssn": "123-45-6789",  # Always Sensitive
                "password": "secret_pass",  # Always Sensitive
                "email": "alice@example.com",  # PII (Role based)
                "public_info": "hello",
            },
        }
        # Guest Role
        cleaned = SensitiveDataFilter.scrub_data(payload, user_role="guest")
        meta = cleaned["metadata"]

        assert "ssn" not in meta
        assert "password" not in meta
        assert "email" not in meta  # Guest can't see email
        assert "public_info" in meta
        assert meta["public_info"] == "hello"

    def test_pii_scrubbing_admin(self):
        payload = {
            "metadata": {
                "ssn": "123",  # Blocked even for admin
                "email": "a@b.com",  # Allowed for admin
            }
        }
        cleaned = SensitiveDataFilter.scrub_data(payload, user_role="admin")
        meta = cleaned["metadata"]

        assert "ssn" not in meta  # Strict blacklist
        assert "email" in meta  # Allowed


# ==========================================
# 2. Test Business Flow Quota (API6)
# ==========================================
class TestExportQuota:
    def test_quota_limits(self):
        # Use Memory Fallback (no redis client passed)
        qm = ExportQuotaManager(redis_client=None)
        user_id = "user_123"

        # 1. Small request (Allowed)
        allowed, msg = qm.check_quota(user_id, 500, "free")
        assert allowed is True

        # 2. Exceed Limit (Free limit is 10k)
        # We already used 500. Try 10,000 more. Total 10,500 > 10,000
        allowed, msg = qm.check_quota(user_id, 10_000, "free")
        assert allowed is False
        assert "limit exceeded" in msg

        # 3. Pro Tier (Limit 1M)
        # Should be allowed even with high count
        allowed, msg = qm.check_quota(user_id, 10_000, "pro")
        assert allowed is True


# ==========================================
# 3. Test Log Integrity (Hash Chain)
# ==========================================
class TestLogChain:
    TEST_LOG_DIR = "tests/logs"
    CRITICAL_FILE = os.path.join(TEST_LOG_DIR, "audit_critical.jsonl")
    CHAIN_FILE = os.path.join(TEST_LOG_DIR, "audit_chain.state")

    @classmethod
    def setup_class(cls):
        os.makedirs(cls.TEST_LOG_DIR, exist_ok=True)

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.TEST_LOG_DIR, ignore_errors=True)

    def test_hash_chaining(self):
        # 1. Setup Logger pointing to test files
        # We need to monkeypatch the file paths since they are module constants in audit_logger.py
        # But importing class allows instance-based, but file paths are hardcoded in methods?
        # Let's inspect audit_logger.py... NO, they are module constants.
        # We can patch them or just inspect the real file effectively if we isolate environment?
        # Better: Create a subclass or modify the instance methods for testing. Or patch 'audit_logger.CRITICAL_LOG_FILE'

        # Monkeypatching for test execution context
        import llm_backend.server.vector_server.core.security.audit_logger as audit_module

        orig_crit = audit_module.CRITICAL_LOG_FILE
        orig_chain = audit_module.CHAIN_STATE_FILE

        audit_module.CRITICAL_LOG_FILE = self.CRITICAL_FILE
        audit_module.CHAIN_STATE_FILE = self.CHAIN_FILE

        try:
            logger = ProductionAuditLogger()
            # Reset chain state
            logger.critical_hash = "0" * 64

            # 2. Log Critical Events (Sync)
            logger._log_tier1_sync({"action": "first", "val": 1})
            logger._log_tier1_sync({"action": "second", "val": 2})

            # 3. Verify File Content
            with open(self.CRITICAL_FILE, "r") as f:
                lines = [json.loads(line) for line in f]

            assert len(lines) == 2
            entry1 = lines[0]
            entry2 = lines[1]

            # Check Hash 1
            # Recalculate hash of entry 1
            # Note: entry1 contains "hash" field. To verify, we must remove it?
            # No, logic is: hash = sha256(prev + json(entry_without_hash))?
            # Wait, let's look at implementation:
            # entry["hash"] = new_hash
            # self._write_to_file...
            # So the stored JSON includes the hash.
            # But the hash calculation was done on the entry BEFORE adding 'hash' key?
            # Let's check code:
            # entry["prev_hash"] = self.critical_hash
            # new_hash = self._compute_hash(self.critical_hash, entry)
            # entry["hash"] = new_hash

            # So correct verification:
            # 1. Take Entry 1 from file.
            # 2. Extract given `hash`.
            # 3. Remove `hash` key.
            # 4. Compute sha256(entry['prev_hash'] + json(entry_without_hash)) ??
            # NO! `_compute_hash` takes (prev_hash, entry).
            # In code: `new_hash = self._compute_hash(self.critical_hash, entry)`
            # AND THEN `entry["hash"] = new_hash`.
            # So the entry passed to `_compute_hash` ALREADY has `prev_hash` but NOT `hash`.

            # Verification Logic:
            stored_hash1 = entry1.pop("hash")
            # prev_hash is inside entry1
            prev_hash1 = "0" * 64  # Initial
            assert entry1["prev_hash"] == prev_hash1

            # Recompute
            serialized = json.dumps(entry1, sort_keys=True)
            computed_hash1 = hashlib.sha256(
                (prev_hash1 + serialized).encode("utf-8")
            ).hexdigest()
            assert computed_hash1 == stored_hash1

            # Check Hash 2
            stored_hash2 = entry2.pop("hash")
            prev_hash2 = entry2["prev_hash"]
            assert prev_hash2 == stored_hash1  # Chain Link!

            serialized2 = json.dumps(entry2, sort_keys=True)
            computed_hash2 = hashlib.sha256(
                (prev_hash2 + serialized2).encode("utf-8")
            ).hexdigest()
            assert computed_hash2 == stored_hash2

        finally:
            audit_module.CRITICAL_LOG_FILE = orig_crit
            audit_module.CHAIN_STATE_FILE = orig_chain
