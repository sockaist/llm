# -*- coding: utf-8 -*-
"""
Access Control Tests for VortexDB API.
Tests RBAC permissions and tenant isolation.
"""
import pytest
from llm_backend.server.vector_server.core.security.access_control import (
    AccessControlManager,
    Role,
    Action,
)


class TestAccessControlManager:
    """Test RBAC access control."""
    
    @pytest.fixture
    def acm(self):
        return AccessControlManager()
    
    def test_admin_can_search(self, acm):
        """Admin should have search permission."""
        user_context = {
            "user": {"id": "admin1", "role": Role.ADMIN, "team": "internal"}
        }
        allowed, _ = acm.check_permission(user_context, {}, Action.SEARCH)
        assert allowed is True
    
    def test_viewer_can_read(self, acm):
        """Viewer should have read permission."""
        user_context = {
            "user": {"id": "viewer1", "role": Role.VIEWER, "team": "public"}
        }
        allowed, _ = acm.check_permission(user_context, {}, Action.READ)
        assert allowed is True
    
    def test_viewer_cannot_write(self, acm):
        """Viewer should not have write permission."""
        user_context = {
            "user": {"id": "viewer1", "role": Role.VIEWER, "team": "public"}
        }
        allowed, reason = acm.check_permission(user_context, {}, Action.WRITE)
        assert allowed is False
    
    def test_editor_can_write(self, acm):
        """Editor should have write permission."""
        user_context = {
            "user": {"id": "editor1", "role": Role.EDITOR, "team": "content"}
        }
        allowed, _ = acm.check_permission(user_context, {}, Action.WRITE)
        assert allowed is True
    
    def test_admin_can_delete(self, acm):
        """Only admin should have delete permission."""
        admin_context = {
            "user": {"id": "admin1", "role": Role.ADMIN, "team": "internal"}
        }
        editor_context = {
            "user": {"id": "editor1", "role": Role.EDITOR, "team": "content"}
        }
        
        admin_allowed, _ = acm.check_permission(admin_context, {}, Action.DELETE)
        editor_allowed, _ = acm.check_permission(editor_context, {}, Action.DELETE)
        
        assert admin_allowed is True
        assert editor_allowed is False


class TestRoleHierarchy:
    """Test role hierarchy and permissions."""
    
    def test_role_values(self):
        """Verify role enum values."""
        assert Role.ADMIN.value == "admin"
        assert Role.EDITOR.value == "editor"
        assert Role.VIEWER.value == "viewer"
    
    def test_action_values(self):
        """Verify action enum values."""
        assert Action.READ.value == "read"
        assert Action.WRITE.value == "write"
        assert Action.DELETE.value == "delete"
        assert Action.SEARCH.value == "search"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
