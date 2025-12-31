from typing import Dict, Any, Tuple
from llm_backend.utils.logger import logger

class FeedbackValidator:
    """
    Phase 8.1: Feedback Quality Management.
    Ensures that only reliable user feedback is used for auto-learning.
    """

    @classmethod
    def validate(cls, feedback_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates feedback based on dwell time, consistency, and bot detection.
        Returns: (is_valid, confidence_level)
        """
        dwell_time = feedback_data.get("dwell_time", 0)
        user_id = feedback_data.get("user_id", "anonymous")
        
        # 1. Dwell Time check (Realistic interaction vs. accidental clicks)
        # Assuming < 2 seconds is accidental, > 3600 seconds is idling
        realistic_time = 2 < dwell_time < 3600
        
        # 2. Duplicate check (Simulated for now)
        is_duplicate = feedback_data.get("is_duplicate", False)
        
        # 3. Bot behavior check (Simulated basic heuristic)
        # Rapid feedbacks within short time from same ID might indicate a bot
        is_bot = feedback_data.get("is_bot", False)
        
        checks = {
            "realistic_time": realistic_time,
            "not_duplicate": not is_duplicate,
            "not_bot": not is_bot
        }
        
        passed_count = sum(checks.values())
        total_checks = len(checks)
        ratio = passed_count / total_checks
        
        if ratio >= 1.0:
            logger.info(f"[Validator] High confidence feedback from {user_id}")
            return True, "high_confidence"
        elif ratio >= 0.75:
            logger.info(f"[Validator] Medium confidence feedback from {user_id}")
            return True, "medium_confidence"
        else:
            logger.warning(f"[Validator] Rejected low quality feedback from {user_id}: {checks}")
            return False, "low_confidence"
