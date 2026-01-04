import re
from typing import Optional
from qdrant_client import models
from llm_backend.utils.logger import logger


class MetadataRouter:
    """
    Phase 7: Universal Metadata Routing.
    Extracts filters from natural language queries to narrow down Qdrant search scope.
    """

    @classmethod
    def extract_filters(cls, query: str) -> Optional[models.Filter]:
        """Parse query for explicit metadata hints using WeakSupervisionEngine."""
        from .weak_supervision import WeakSupervisionEngine

        must_conditions = []

        # 1. Year Extraction (Regex is still deterministic enough for years)
        year_match = re.search(r"(\d{4})년", query)
        if year_match:
            year = year_match.group(1)
            must_conditions.append(
                models.FieldCondition(key="year", match=models.MatchValue(value=year))
            )
            logger.info(f"[Router] Extracted year: {year}")

        # 2. Fuzzy Department Extraction
        dept_res = WeakSupervisionEngine.predict(query, "department", threshold=0.5)
        if dept_res:
            dept, conf = dept_res
            must_conditions.append(
                models.FieldCondition(
                    key="department", match=models.MatchValue(value=dept)
                )
            )
            logger.info(f"[Router] Fuzzy department: {dept} (conf={conf:.2f})")

        # 3. Fuzzy Category Extraction
        cat_res = WeakSupervisionEngine.predict(query, "category", threshold=0.5)
        if cat_res:
            cat, conf = cat_res
            must_conditions.append(
                models.FieldCondition(
                    key="category", match=models.MatchValue(value=cat)
                )
            )
            logger.info(f"[Router] Fuzzy category: {cat} (conf={conf:.2f})")

        if not must_conditions:
            return None

        return models.Filter(must=must_conditions)
