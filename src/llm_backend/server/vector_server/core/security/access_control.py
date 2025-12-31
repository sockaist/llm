# -*- coding: utf-8 -*-
from typing import Dict, List, Optional, Tuple, Any
import datetime
from enum import Enum
from llm_backend.utils.logger import logger

class Role(str, Enum):
    ADMIN = "admin"        # Full Access
    ENGINEER = "engineer"  # Read/Write/Delete
    ANALYST = "analyst"    # Read/Search
    VIEWER = "viewer"      # Read Only
    SERVICE = "service"    # Internal Service

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
    Role.VIEWER: {Action.READ},
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
            "feedback_worker"
        }

    def verify_service_call(self, service_id: str, resource: Dict[str, Any], action: str) -> Tuple[bool, str]:
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
    def __init__(self):
        self.service_auth = ServiceAuthManager()
        logger.info("[AccessControl] Initialized with Hybrid RBAC/ABAC model")

    def check_permission(self, context: Dict[str, Any], resource: Dict[str, Any], action: str) -> Tuple[bool, str]:
        """
        Main entry point for permission checking.
        """
        # 1. Service-to-Service check
        if context.get("type") == "service":
            service_id = context.get("user", {}).get("id") or context.get("service_id")
            if service_id:
                return self.service_auth.verify_service_call(service_id, resource, action)
            return False, "missing_service_id"

        # 2. Extract User Context
        user_info = context.get("user", {})
        user_id = user_info.get("id")
        user_role = user_info.get("role", Role.VIEWER)
        user_team = user_info.get("team")
        
        # 3. RBAC Check (Base Permissions)
        rbac_allowed = self._check_rbac(user_role, action)
        
        # 4. ABAC Policy Check (Refinement & Overrides)
        abac_decision, abac_reason = self._check_abac(user_info, resource, action, rbac_allowed)
        
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
        allowed_actions = RBAC_POLICIES.get(role, set())
        if Action.ALL in allowed_actions:
            return True
        return action in allowed_actions

    def _check_abac(self, user: Dict[str, Any], resource: Dict[str, Any], action: str, rbac_allowed: bool) -> Tuple[Optional[bool], str]:
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
                    return False, f"abac:team_mismatch(user={user_team}, res={resource_team})"
        
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
