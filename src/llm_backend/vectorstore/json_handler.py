from typing import Dict, Any, Optional, List


class JSONProcessor:
    """
    Heuristically extracts standardized fields (content, title, url) from arbitrary JSON documents.
    """

    CONTENT_KEYS = [
        "content",
        "contents",
        "body",
        "text",
        "description",
        "summary",
        "abstract",
        "answer",
        "response",
    ]
    TITLE_KEYS = ["title", "subject", "name", "headline", "topic", "question"]
    URL_KEYS = ["url", "link", "source", "href", "website", "uri"]

    @classmethod
    def process_document(cls, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a document by extracting standard fields and applying defaults.
        Returns a copy of the document with standardized 'content', 'title', 'url' fields added/ensured.
        """
        normalized = doc.copy()

        # 1. Extract Content (Critical)
        if "content" not in normalized or not normalized["content"]:
            found_content = cls._find_value(doc, cls.CONTENT_KEYS)
            if found_content:
                normalized["content"] = found_content
            else:
                # Fallback: Serialize the entire document to string
                # This ensures custom JSONs without explicit 'content' key are still indexed.
                # We exclude system keys if possible, but dumping everything is safest.
                try:
                    import json
                    # Sort keys for deterministic content
                    normalized["content"] = json.dumps(doc, ensure_ascii=False, sort_keys=True)
                except Exception:
                    pass

        # 2. Extract Title
        if "title" not in normalized:
            found_title = cls._find_value(doc, cls.TITLE_KEYS)
            if found_title:
                normalized["title"] = found_title
            else:
                normalized["title"] = "Untitled"

        # 3. Extract URL
        if "url" not in normalized:
            found_url = cls._find_value(doc, cls.URL_KEYS)
            if found_url:
                normalized["url"] = found_url

        # 4. Apply Defaults
        if "access_level" not in normalized:
            normalized["access_level"] = 1  # Default Public
        if "tenant_id" not in normalized:
            normalized["tenant_id"] = "public"

        return normalized

    @staticmethod
    def _find_value(doc: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for key in keys:
            # Case-insensitive check?
            # For simplicity, check exact key first, then case-insensitive
            if key in doc and isinstance(doc[key], str) and doc[key].strip():
                return doc[key]

            # Case insensitive scan (more expensive, maybe needed?)
            # Let's stick to direct keys first.

        # Extended Case-Insensitive Search
        doc_keys_lower = {k.lower(): k for k in doc.keys()}
        for key in keys:
            if key in doc_keys_lower:
                real_key = doc_keys_lower[key]
                val = doc[real_key]
                if isinstance(val, str) and val.strip():
                    return val

        return None
