import asyncio
import os
import sys
from llm_backend.utils.logger import logger

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from llm_backend.vectorstore.dynamic_db import dynamic_db
from llm_backend.vectorstore.feedback_validator import FeedbackValidator
from llm_backend.vectorstore.metrics_collector import MetricsCollector


async def test_stability():
    logger.info("Phase 8.1 Stability Verification")

    # 1. Feedback Validation Test (Rejection)
    logger.info("Test 1: Rejecting Low Quality Feedback (Short dwell time)")
    user_action_bad = {"dwell_time": 1, "user_id": "test_bot"}
    is_valid, _ = FeedbackValidator.validate(user_action_bad)
    logger.info(f"Result: is_valid={is_valid}")

    # 2. Feedback Validation Test (Acceptance)
    logger.info("Test 2: Accepting High Quality Feedback")
    user_action_good = {"dwell_time": 120, "user_id": "real_user_1"}
    is_valid, conf = FeedbackValidator.validate(user_action_good)
    logger.info(f"Result: is_valid={is_valid}, Confidence={conf}")

    # 3. Dynamic DB Stability: Atomic Save & Backup
    logger.info("Test 3: Verifying Atomic Save and Backup Creation")
    dynamic_db.add_feedback(
        "category", "CS class", "graduation", feedback_score=1.0, validator_conf=conf
    )

    backup_dir = dynamic_db.BACKUP_DIR
    backups = os.listdir(backup_dir)
    logger.info(f"Result: Found {len(backups)} backups in {backup_dir}")

    # 4. Metrics Collection
    logger.info("Test 4: System Health Metrics")
    stats = MetricsCollector.get_rule_stats()
    logger.info(
        f"Result: Stats Summary - Total Rules: {stats['total_rules']}, High Confidence: {stats['high_conf']}"
    )

    # 5. AB Test Assignment
    from llm_backend.vectorstore.ab_test import ABTestFramework

    logger.info("Test 5: A/B Test Group Assignment")
    group_a = ABTestFramework.get_user_group("user_a")
    group_b = ABTestFramework.get_user_group("user_b")
    logger.info(f"Result: User A -> {group_a}, User B -> {group_b}")


if __name__ == "__main__":
    asyncio.run(test_stability())
