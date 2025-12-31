
from typing import Dict, Any, List

class AccessControl:
    """
    Centralized Permission Logic for Multi-Tenancy.
    Handles 'can_edit', 'can_view', 'can_delete' and Security Level updates.
    """

    ALLOWED_LEVELS = {
        "admin": [1, 2, 3, 4],
        "editor": [1, 2, 3],
        "viewer": [1, 2],
        "guest": [1]
    }

    @classmethod
    def get_allowed_levels(cls, role: str) -> List[int]:
        return cls.ALLOWED_LEVELS.get(role, [1])

    @staticmethod
    def can_view_document(user_context: Dict[str, Any], doc_meta: Dict[str, Any]) -> bool:
        """
        Check if user can VIEW a document.
        Logic parallels Qdrant filter but applied to retrieved objects.
        """
        user_id = user_context.get("user_id", "anonymous")
        role = user_context.get("role", "guest")
        
        doc_tenant = doc_meta.get("tenant_id", "public")
        doc_level = doc_meta.get("access_level", 1)

        # 1. Admin: Public Only (Level 1-4)
        if role == "admin":
            return doc_tenant == "public"
        
        # 2. Owner: Always can view own documents
        if doc_tenant == user_id:
            return True
            
        # 3. Public Doc: Check Security Levels
        if doc_tenant == "public":
            allowed = AccessControl.get_allowed_levels(role)
            return doc_level in allowed
            
        return False

    @staticmethod
    def can_edit_document(user_context: Dict[str, Any], doc_meta: Dict[str, Any]) -> bool:
        """
        Check if user can EDIT content/metadata.
        """
        user_id = user_context.get("user_id")
        role = user_context.get("role", "guest")
        doc_tenant = doc_meta.get("tenant_id", "public")
        
        # Admin: Can edit PUBLIC documents only
        if role == "admin":
            return doc_tenant == "public"
            
        # User: Can edit OWN documents only
        if doc_tenant == user_id:
            return True
            
        # Others (Editor/Viewer) cannot edit public docs unless we add "Editor" logic for public.
        # For now, sticking to "Admin manages public, User manages private".
        return False

    @staticmethod
    def can_change_security_level(user_context: Dict[str, Any], doc_meta: Dict[str, Any]) -> bool:
        """
        Check if user can change the 'access_level' field.
        """
        user_context.get("user_id")
        role = user_context.get("role", "guest")
        doc_tenant = doc_meta.get("tenant_id", "public")
        
        # Only Admin can change security level of PUBLIC documents
        if role == "admin" and doc_tenant == "public":
            return True
            
        # Users cannot change security level of Private documents? 
        # (Maybe they can, but it doesn't matter much as they are the only viewer).
        # Let's restrict it to Admin for public docs for now.
        return False
