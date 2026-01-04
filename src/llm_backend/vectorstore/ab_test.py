import hashlib
from llm_backend.utils.logger import logger


class ABTestFramework:
    """
    Phase 8.1: A/B Testing Framework.
    Assigns users to Control or Treatment groups and collects metrics.
    """

    GROUPS = ["control", "treatment"]

    @classmethod
    def get_user_group(cls, user_id: str) -> str:
        """Deterministically assign user to a group based on ID hash."""
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        group = cls.GROUPS[hash_val % len(cls.GROUPS)]
        logger.debug(f"[ABTest] User {user_id} assigned to group: {group}")
        return group

    @classmethod
    def should_use_fuzzy(cls, user_id: str) -> bool:
        """Treatment group uses Fuzzy/AL, Control uses static baseline."""
        group = cls.get_user_group(user_id)
        return group == "treatment"

    @classmethod
    def collect_metrics(cls, group: str, action_type: str, success: bool):
        """
        Placeholder for metric collection.
        In production, this would send data to Prometheus or a DB.
        """
        status = "Success" if success else "Failure"
        logger.info(
            f"[ABTest] Metirc: Group={group}, Action={action_type}, Status={status}"
        )
