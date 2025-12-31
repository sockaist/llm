from typing import Dict, Any
from .dynamic_db import dynamic_db
from llm_backend.utils.logger import logger

class MetricsCollector:
    """
    Phase 8.1: Monitoring and Metrics.
    Collects real-time statistics about the learning system.
    """

    @classmethod
    def get_rule_stats(cls) -> Dict[str, Any]:
        """Summarize rule health status."""
        stats = {
            "total_rules": 0,
            "high_conf": 0, # > 0.8
            "med_conf": 0,  # 0.5 - 0.8
            "low_conf": 0,   # < 0.5
            "fields": {}
        }
        
        for field in ["department", "category", "entities"]:
            rules = dynamic_db.get_rules(field)
            stats["fields"][field] = len(rules)
            stats["total_rules"] += len(rules)
            
            for keyword, data in rules.items():
                conf = data.get("confidence", 0.0)
                if conf >= 0.8:
                    stats["high_conf"] += 1
                elif conf >= 0.5:
                    stats["med_conf"] += 1
                else:
                    stats["low_conf"] += 1
        
        logger.info(f"[Metrics] System Status: Total={stats['total_rules']}, High={stats['high_conf']}")
        return stats

    @classmethod
    def log_feedback_event(cls, validator_conf: str, success: bool):
        """Log a learning event for monitoring trends."""
        logger.info(f"[Metrics] Learning Event: Quality={validator_conf}, Success={success}")
