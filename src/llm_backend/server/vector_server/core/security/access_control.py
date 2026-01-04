# -*- coding: utf-8 -*-
from typing import Dict, List, Optional, Tuple, Any
import datetime
from enum import Enum
from llm_backend.utils.logger import logger


class Role(str, Enum):
    ADMIN = "admin"  # Full Access
    ENGINEER = "engineer"  # Read/Write/Delete
    ANALYST = "analyst"  # Read/Search
    VIEWER = "viewer"  # Read Only
    GUEST = "guest"  # Public Access
    SERVICE = "service"  # Internal Service


class Action(str, Enum):
    # Resource Actions
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SEARCH = "search"

    # Admin Actions
    MANAGE_USERS = "manage_users"
    MANAGE_CONFIG = "manage_config"
    VIEW_AUDIT = "view_audit"
    EXPORT_DATA = "export_data"

    # Universal wildcards
    ALL = "*"


# Base RBAC Definitions
RBAC_POLICIES = {
    Role.ADMIN: {Action.ALL},
    Role.ENGINEER: {Action.READ, Action.WRITE, Action.DELETE, Action.SEARCH},
    Role.ANALYST: {Action.READ, Action.SEARCH},
    Role.VIEWER: {Action.READ, Action.SEARCH},
    Role.GUEST: {Action.READ, Action.SEARCH},
    Role.SERVICE: {Action.READ, Action.WRITE},  # Service can typically write data
}


class ServiceAuthManager:
    """
    Manages internal service-to-service authentication trust.
    In a real system, this would verify JWTs signed by an internal CA or mTLS.
    """

    def __init__(self):
        # MVP: Whitelisted internal service IDs
        self.whitelisted_services = {
            "ingest_worker",
            "dashboard_api",
            "feedback_worker",
        }

    def verify_service_call(
        self, service_id: str, resource: Dict[str, Any], action: str
    ) -> Tuple[bool, str]:
        if service_id in self.whitelisted_services:
            logger.debug(f"[ServiceAuth] Verified call from {service_id}")
            return True, f"service_auth:{service_id}"
        logger.warning(f"[ServiceAuth] Denied call from unknown service: {service_id}")
        return False, "unknown_service"


class AccessControlManager:
    """
    Hybrid RBAC + ABAC Access Control Manager.
    Layer 1 of the Security Architecture.
    """

    def __init__(self, config=None):
        self.service_auth = ServiceAuthManager()
        self.config = config
        self._rbac_policies = RBAC_POLICIES.copy()
        
        # Override or extend RBAC policies from config
        if self.config and hasattr(self.config.security.authorization, "roles"):
            # Example logic: if config defines roles/permissions, update _rbac_policies
            # For now, we'll keep the defaults but allow future extensibility
            pass
            
        logger.info("[AccessControl] Initialized with Hybrid RBAC/ABAC model")

    def check_permission(
        self, context: Dict[str, Any], resource: Dict[str, Any], action: str
    ) -> Tuple[bool, str]:
        """
        Main entry point for permission checking.
        """
        # 1. Service-to-Service check
        if context.get("type") == "service":
            # Exception: Allow ADMIN to bypass service whitelist (e.g. CLI operations via API Key)
            user_role = context.get("user", {}).get("role")
            if user_role == Role.ADMIN:
                 return True, "admin_override"

            service_id = context.get("user", {}).get("id") or context.get("service_id")
            if service_id:
                return self.service_auth.verify_service_call(
                    service_id, resource, action
                )
            return False, "missing_service_id"

        # 2. Extract User Context (Robust extraction for backward compatibility)
        user_info = context.get("user")
        if user_info and isinstance(user_info, dict):
            user_id = user_info.get("id")
            user_role = user_info.get("role", Role.VIEWER)
            user_team = user_info.get("team")
        else:
            # Fallback to top-level for older context structures
            user_id = context.get("user_id") or context.get("id")
            user_role = context.get("role", Role.VIEWER)
            user_team = context.get("team")
            user_info = {"id": user_id, "role": user_role, "team": user_team}

        # 3. RBAC Check (Base Permissions)
        rbac_allowed = self._check_rbac(user_role, action)

        # 4. ABAC Policy Check (Refinement & Overrides)
        abac_decision, abac_reason = self._check_abac(
            user_info, resource, action, rbac_allowed
        )

        if abac_decision is not None:
            return abac_decision, abac_reason

        # Fallback to RBAC
        if rbac_allowed:
            return True, f"rbac:{user_role}"

        return False, f"rbac_denied:{user_role}"

    def _check_rbac(self, role: str, action: str) -> bool:
        """
        Standard Role-Based Access Control check.
        """
        allowed_actions = self._rbac_policies.get(role, set())
        if Action.ALL in allowed_actions:
            return True
        return action in allowed_actions

    def _check_abac(
        self,
        user: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        rbac_allowed: bool,
    ) -> Tuple[Optional[bool], str]:
        """
        Attribute-Based Access Control logic.
        Returns (Bool, Reason) if a policy matches, else (None, "")
        """
        # Policy 1: Team Isolation (Analysts/Engineers only access their team's resources)
        # Admins bypass this.
        user_role = user.get("role")
        if user_role != Role.ADMIN:
            resource_team = resource.get("team")
            user_team = user.get("team")

            # If resource is tagged with a team, user must match
            if resource_team and resource_team != "public":
                if user_team != resource_team:
                    return (
                        False,
                        f"abac:team_mismatch(user={user_team}, res={resource_team})",
                    )

        # Policy 2: Time-based Access for Viewers/External (e.g., Contractors)
        # This is an example policy.
        if user.get("is_contractor"):
            now = datetime.datetime.now().time()
            start_time = datetime.time(9, 0)
            end_time = datetime.time(18, 0)
            if not (start_time <= now <= end_time):
                return False, "abac:outside_business_hours"

        # Policy 3: Emergency "Break-the-Glass"
        if user.get("emergency_access"):
            logger.warning(f"[AccessControl] EMERGENCY ACCESS used by {user.get('id')}")
            return True, "abac:emergency_access"

        return None, ""

    # --- Document Level Permissions (Consolidated from legacy AccessControl) ---

    @staticmethod
    def _get_allowed_levels(role: str) -> List[int]:
        levels = {
            Role.ADMIN: [1, 2, 3, 4],
            Role.ENGINEER: [1, 2, 3],
            Role.ANALYST: [1, 2],
            Role.VIEWER: [1, 2],
            Role.GUEST: [1],
        }
        return levels.get(role, [1])

    def can_view_document(
        self, context: Dict[str, Any], doc_meta: Dict[str, Any]
    ) -> bool:
        # Robust extraction
        user_info = context.get("user")
        if user_info and isinstance(user_info, dict):
            user_id = user_info.get("id", "anonymous")
            role = user_info.get("role", Role.GUEST)
        else:
            user_id = context.get("user_id") or context.get("id", "anonymous")
            role = context.get("role", Role.GUEST)

        doc_tenant = doc_meta.get("tenant_id", "public")
        doc_level = doc_meta.get("access_level", 1)

        if role == Role.ADMIN:
            return doc_tenant == "public"
        if doc_tenant == user_id:
            return True
        if doc_tenant == "public":
            allowed = self._get_allowed_levels(role)
            return doc_level in allowed
        return False

    def can_edit_document(
        self, context: Dict[str, Any], doc_meta: Dict[str, Any]
    ) -> bool:
        # Robust extraction
        user_info = context.get("user")
        if user_info and isinstance(user_info, dict):
            user_id = user_info.get("id")
            role = user_info.get("role", Role.GUEST)
        else:
            user_id = context.get("user_id") or context.get("id")
            role = context.get("role", Role.GUEST)
            
        doc_tenant = doc_meta.get("tenant_id", "public")
        
        logger.debug(f"[AccessControl] can_edit: user={user_id}, role={role}, doc_tenant={doc_tenant}")

        if role == Role.ADMIN:
            return doc_tenant == "public"
        if doc_tenant == user_id:
            return True
        return False

    def can_change_security_level(
        self, context: Dict[str, Any], doc_meta: Dict[str, Any]
    ) -> bool:
        # Robust extraction
        user_info = context.get("user")
        if user_info and isinstance(user_info, dict):
            role = user_info.get("role", Role.GUEST)
            user_id = user_info.get("id")
        else:
            role = context.get("role", Role.GUEST)
            user_id = context.get("user_id") or context.get("id")

        doc_tenant = doc_meta.get("tenant_id", "public")
        
        logger.debug(f"[AccessControl] can_change_level: user={user_id}, role={role}, doc_tenant={doc_tenant}")

        if role == Role.ADMIN and doc_tenant == "public":
            return True
        return False
