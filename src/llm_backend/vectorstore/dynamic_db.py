import json
import os
import re
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from llm_backend.utils.logger import logger


class DynamicRuleDatabase:
    """
    Phase 8.1: Advanced Dynamic Rule Database.
    Includes stability features: Atomic writes, Backups, Confidence Capping, and Time Decay.
    """

    DEFAULT_RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")
    BACKUP_DIR = os.path.join(os.path.dirname(__file__), "backups")
    CONFIDENCE_CAP = 0.98
    DECAY_THRESHOLD_DAYS = 30
    DECAY_FACTOR = 0.95

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self.DEFAULT_RULES_PATH
        self.rules = {}
        if not os.path.exists(self.BACKUP_DIR):
            os.makedirs(self.BACKUP_DIR)
        self.load()

    def load(self):
        """Load rules from disk and apply time decay."""
        if not os.path.exists(self.db_path):
            logger.warning(
                f"[DynamicDB] File not found: {self.db_path}. Using empty rules."
            )
            self.rules = {"department": {}, "category": {}, "entities": {}}
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
            logger.info(f"[DynamicDB] Loaded rules from {self.db_path}")

            # Phase 8.1: Apply time-based decay
            self._apply_decay()
        except Exception as e:
            logger.error(f"[DynamicDB] Error loading rules: {e}")
            self.rules = {"department": {}, "category": {}, "entities": {}}

    def _apply_decay(self):
        """Decrease confidence of rules that haven't been updated recently."""
        now = datetime.now()
        decayed_count = 0

        for field in self.rules:
            if not isinstance(self.rules[field], dict):
                continue
            for keyword, data in self.rules[field].items():
                last_updated_str = data.get("last_updated")
                if not last_updated_str:
                    continue

                last_updated = datetime.fromisoformat(last_updated_str)
                if now - last_updated > timedelta(days=self.DECAY_THRESHOLD_DAYS):
                    old_conf = data.get("confidence", 0.5)
                    data["confidence"] = max(0.0, old_conf * self.DECAY_FACTOR)
                    data["last_updated"] = now.isoformat()  # Mark the decay
                    decayed_count += 1

        if decayed_count > 0:
            logger.info(f"[DynamicDB] Applied decay to {decayed_count} rules.")
            self.save()

    def save(self):
        """Save rules to disk using atomic write and create backup."""
        try:
            # 1. Create Backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"rules_backup_{timestamp}.json"
            backup_path = os.path.join(self.BACKUP_DIR, backup_name)

            if os.path.exists(self.db_path):
                shutil.copy(self.db_path, backup_path)

            # 2. Atomic Write
            temp_path = self.db_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)

            os.replace(temp_path, self.db_path)

            # 3. Cleanup old backups (keep last 10)
            backups = sorted(
                [
                    f
                    for f in os.listdir(self.BACKUP_DIR)
                    if f.startswith("rules_backup_")
                ]
            )
            if len(backups) > 10:
                for b in backups[:-10]:
                    os.remove(os.path.join(self.BACKUP_DIR, b))

            logger.info(
                f"[DynamicDB] Atomic save successful. Backup created: {backup_name}"
            )
        except Exception as e:
            logger.error(f"[DynamicDB] Error saving rules: {e}")

    def add_feedback(
        self,
        field: str,
        query: str,
        value: Any,
        feedback_score: float = 0.8,
        validator_conf: str = "high_confidence",
    ):
        """
        Update/Add a rule based on validated user feedback.
        """
        if field not in self.rules:
            self.rules[field] = {}

        keywords = self._extract_keywords(query)
        if not keywords:
            return

        best_keyword = max(keywords, key=len)

        # Step 1: Weight based on validator confidence
        weight_map = {
            "high_confidence": 0.30,
            "medium_confidence": 0.15,
            "low_confidence": 0.0,
        }
        update_weight = weight_map.get(validator_conf, 0.0)

        if update_weight == 0.0:
            logger.warning(
                "[DynamicDB] Feedback ignored due to low validator confidence."
            )
            return

        now_iso = datetime.now().isoformat()

        if best_keyword not in self.rules[field]:
            # Initial confidence set to 0.5 (Neutral)
            if field == "entities":
                self.rules[field][best_keyword] = {
                    "related": [value] if not isinstance(value, list) else value,
                    "confidence": 0.5,
                    "last_updated": now_iso,
                }
            else:
                self.rules[field][best_keyword] = {
                    "value": value,
                    "confidence": 0.5,
                    "last_updated": now_iso,
                }
            logger.info(f"[DynamicDB] Learned new rule: {best_keyword} -> {value}")

        # Step 2: Update confidence with weight and cap
        rule = self.rules[field][best_keyword]
        current_conf = rule.get("confidence", 0.5)

        # Use a more sophisticated update (weighted deviation toward feedback)
        # feedback_score is assumed to be 1.0 (positive) or -1.0 (negative)
        new_conf = current_conf + (feedback_score * update_weight)

        # Step 3: Apply CAP
        rule["confidence"] = min(self.CONFIDENCE_CAP, max(0.0, new_conf))
        rule["last_updated"] = now_iso

        logger.info(
            f"[DynamicDB] Confidence updated for '{best_keyword}': {current_conf:.2f} -> {rule['confidence']:.2f}"
        )
        self.save()

    def _extract_keywords(self, query: str) -> List[str]:
        """Simple keyword extraction for learning."""
        words = re.findall(r"\w+", query.lower())
        return [w for w in words if len(w) >= 2]

    def get_rules(self, field: str) -> Dict[str, Any]:
        """Return rules for a specific field."""
        return self.rules.get(field, {})


# Singleton instance
dynamic_db = DynamicRuleDatabase()
