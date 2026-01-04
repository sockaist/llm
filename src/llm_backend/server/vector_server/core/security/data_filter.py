# llm_backend/server/vector_server/core/security/data_filter.py
from typing import Dict, List, Union


class SensitiveDataFilter:
    """
    OWASP API3: Broken Object Property Level Authorization Defense.
    Filters out sensitive fields from API responses (PII Scrubbing).
    """

    # Default sensitive keys to always block in metadata
    SENSITIVE_KEYS = {
        "ssn",
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "credit_card",
        "cc_number",
        "cvv",
        "pin",
        "auth_token",
        "jwt",
        "access_token",
        "refresh_token",
        "private_key",
        "internal_id",
    }

    # Conditional PII keys (Blocked for non-admins unless explicitly allowed)
    PII_KEYS = {
        "email",
        "phone",
        "phone_number",
        "mobile",
        "address",
        "dob",
        "birthdate",
        "salary",
    }

    @classmethod
    def scrub_data(
        cls, data: Union[Dict, List], user_role: str = "guest"
    ) -> Union[Dict, List]:
        """
        Recursively remove sensitive keys from dictionary or list of dictionaries.
        """
        if isinstance(data, list):
            return [cls.scrub_data(item, user_role) for item in data]

        if not isinstance(data, dict):
            return data

        # Shallow copy to avoid mutating original data if it's used elsewhere
        # Deep copy is safer if nested, but slower.
        # For API response scrubbing, usually we are constructing a new response dict anyway.
        # But `data` here might be the `payload` dict from Qdrant.
        cleaned = {}

        for k, v in data.items():
            key_lower = k.lower()

            # 1. Block High-Risk Keys Always (Unless internal logic bypasses this filter)
            if key_lower in cls.SENSITIVE_KEYS:
                continue

            # 2. Block PII for non-admins
            if key_lower in cls.PII_KEYS and user_role != "admin":
                continue

            # 3. Recursion
            if isinstance(v, (dict, list)):
                cleaned[k] = cls.scrub_data(v, user_role)
            else:
                cleaned[k] = v

        return cleaned

    @classmethod
    def filter_search_results(
        cls, results: List[Dict], user_context: Dict
    ) -> List[Dict]:
        """
        Helper for search results (list of scored points).
        Structure usually: [{'id':..., 'payload': {...}, 'score':...}, ...]
        """
        role = user_context.get("user", {}).get("role", "guest")

        cleaned_results = []
        for res in results:
            # We must be careful not to modify the original cached object if it's from cache
            # So we deepcopy or construct new dict.
            new_res = res.copy()

            # Filter 'payload' or 'metadata'
            if "payload" in new_res and new_res["payload"]:
                new_res["payload"] = cls.scrub_data(new_res["payload"], role)

            if "metadata" in new_res and new_res["metadata"]:
                new_res["metadata"] = cls.scrub_data(new_res["metadata"], role)

            cleaned_results.append(new_res)

        return cleaned_results


class MetadataValidator:
    """
    Prevents Privilege Escalation via Metadata Injection.
    Blocks users from setting reserved system fields.
    """

    RESERVED_FIELDS = {
        "role",
        "permissions",
        "is_admin",
        "admin",
        "verified",
        "tier",
        "tenant_id",
        "_internal",
        "auth_level",
        "system_tags",
    }

    @classmethod
    def validate_input(cls, data: Dict, user_role: str = "guest") -> Union[bool, str]:
        """
        Check if input data contains reserved fields.
        Returns (True, "ok") or (False, "error message").
        Admins might be allowed to set these, but usually even admins shouldn't set
        system-managed fields via generic upsert.
        """
        # If Admin, maybe allow? For now, block for safety unless we have a specific Admin override API.
        # Strict security: Block these in standard CRUD.

        for key in data.keys():
            if key.lower() in cls.RESERVED_FIELDS:
                return False, f"Reserved field '{key}' is not allowed in metadata."

        # Check nested metadata if it exists
        if "metadata" in data and isinstance(data["metadata"], dict):
            for key in data["metadata"].keys():
                if key.lower() in cls.RESERVED_FIELDS:
                    return False, f"Reserved field '{key}' is not allowed in metadata."

        return True, "ok"
