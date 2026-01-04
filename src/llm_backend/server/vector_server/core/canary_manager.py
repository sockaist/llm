import os
import random
from typing import Dict, Any


class CanaryManager:
    """
    Manages Canary deployments and feature flags.
    Allows testing new features on a subset of users or via explicit headers.
    """

    _instance = None

    def __init__(self):
        # Read percentage from env (0-100)
        self.canary_percentage = int(os.getenv("CANARY_PERCENTAGE", "0"))

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_active(
        self, user_context: Dict[str, Any] = None, headers: Dict[str, Any] = None
    ) -> bool:
        """
        Determine if Canary features should be active for this request.
        Logic:
        1. Explicit Override via Header (X-Canary: true)
        2. Random Rollout (CANARY_PERCENTAGE)
        """
        # 1. Check Header
        if headers:
            x_canary = headers.get("x-canary", "").lower()
            if x_canary == "true":
                return True

        # 2. Random Rollout (if pct > 0)
        if self.canary_percentage > 0:
            # Deterministic for user if user_id is present?
            # Ideally hash(user_id) % 100 < pct
            # For simplicity, keeping it random per request or simple random.
            # Let's try deterministic if user_id exists.
            if user_context and user_context.get("user_id"):
                user_id = user_context.get("user_id")
                if user_id != "anonymous":
                    import hashlib

                    h = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
                    return (h % 100) < self.canary_percentage

            # Pure random fallback
            return random.randint(0, 99) < self.canary_percentage

        return False
