# src/tests/test_security_fuzz.py
import pytest
import random
import string
from llm_backend.server.vector_server.core.security.defense import defense_system
from llm_backend.server.vector_server.core.security.access_control import (
    AccessControlManager,
    Action,
    Role,
)

# Initialize Manager
access_manager = AccessControlManager()


class TestSecurityFuzzing:
    def test_fuzz_injection_detection(self):
        """
        Fuzz validator with random text (Manual Fuzzing).
        """
        for _ in range(100):
            # Generate random string
            length = random.randint(1, 100)
            query = "".join(
                random.choices(
                    string.ascii_letters + string.digits + string.punctuation, k=length
                )
            )

            # Inject SQL/Prompt keywords occasionally
            if random.random() < 0.2:
                query += " UNION SELECT "
            if random.random() < 0.2:
                query += " Ignore previous instructions "

            try:
                is_detected, reason = defense_system.injection_detector.detect(query)
                if is_detected:
                    assert reason != ""
                    assert "pattern_match" in reason
            except Exception as e:
                pytest.fail(f"Crash on input '{query}': {e}")

    def test_fuzz_anomaly_detection(self):
        """
        Fuzz anomaly detector with random vectors.
        """
        for _ in range(100):
            vec_len = random.randint(1, 128)
            # Random floats
            vector = [random.uniform(-10.0, 10.0) for _ in range(vec_len)]

            # Occasionally inject huge number
            if random.random() < 0.1:
                idx = random.randint(0, vec_len - 1)
                vector[idx] = 1e6

            try:
                bad, reason = defense_system.anomaly_detector.is_anomalous(vector)
                if bad:
                    assert reason != ""
            except Exception as e:
                pytest.fail(f"Crash on vector {vector}: {e}")

    def test_fuzz_access_control(self):
        """
        Fuzz Access Control.
        """
        roles = [
            Role.ADMIN,
            Role.ENGINEER,
            Role.ANALYST,
            Role.VIEWER,
            "hacker",
            "unknown",
        ]
        actions = [
            Action.READ,
            Action.WRITE,
            Action.DELETE,
            Action.SEARCH,
            "execute_exploit",
            "drop_db",
        ]

        for _ in range(100):
            role = random.choice(roles)
            action = random.choice(actions)

            ctx = {"user": {"role": role, "team": "TeamRandom"}}
            resource = {"team": "TeamRandom"}

            try:
                allowed, reason = access_manager.check_permission(ctx, resource, action)
                if role == Role.ADMIN:
                    assert allowed
                if role == "hacker":
                    assert not allowed
            except Exception as e:
                pytest.fail(f"Crash on role={role}, action={action}: {e}")
