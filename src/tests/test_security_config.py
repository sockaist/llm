import pytest
import os
import shutil
import yaml
from datetime import datetime, timedelta
from llm_backend.server.vector_server.config.security_config import load_configuration, VectorDBConfig
from llm_backend.server.vector_server.config.security_profiles import SecurityProfiles
from llm_backend.server.vector_server.config.security_validator import SecurityValidator

class TestSecurityConfig:
    TEST_CONFIG = "vectordb_test.yaml"

    def setup_method(self):
        # Ensure clean slate
        if os.path.exists(self.TEST_CONFIG):
            os.remove(self.TEST_CONFIG)

    def teardown_method(self):
        if os.path.exists(self.TEST_CONFIG):
            os.remove(self.TEST_CONFIG)

    def test_load_all_profiles(self):
        """Ensure all defined profiles are valid Pydantic models"""
        profiles = SecurityProfiles.list_profiles()
        for p in profiles:
            name = p["name"]
            data = SecurityProfiles.get_profile(name)["config"]
            # Should not raise validation error
            config = VectorDBConfig(**data)
            assert config.security.tier == p["tier"]

    def test_validation_tier2_requirements(self):
        """Tier 2 requires MFA and Log Integrity"""
        # Create invalid Tier 2 config
        data = SecurityProfiles.get_profile("production_enhanced")["config"]
        # Disable MFA
        data["security"]["authentication"]["mfa"]["enabled"] = False
        
        config = VectorDBConfig(**data)
        warnings = SecurityValidator.validate_config(config)
        
        # Should have blocking warning
        blocking = [w for w in warnings if w.blocking]
        assert len(blocking) > 0
        assert "MFA required for Tier 2+" in blocking[0].message

    def test_override_logic_valid(self):
        """Override allows bypassing rules if valid"""
        data = SecurityProfiles.get_profile("production_enhanced")["config"]
        # Disable MFA but add override
        data["security"]["authentication"]["mfa"]["enabled"] = False
        
        expires = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        data["security"]["overrides"] = {
            "authentication": {
                "mfa": {
                    "reason": "Test Override",
                    "approved_by": "sec_team",
                    "expires": expires
                }
            }
        }
        
        config = VectorDBConfig(**data)
        warnings = SecurityValidator.validate_config(config)
        
        # Should NOT have blocking warning about MFA
        # But we haven't implemented logic to suppress warning if override exists in validate_config completely?
        # Let's check `security_validator.py`
        # Logic: if not (mfa enabled): check override. 
        # In code: if "authentication" in overrides and "mfa" in overrides... pass
        
        blocking = [w for w in warnings if w.blocking]
        assert len(blocking) == 0

    def test_override_expired(self):
        """Expired override should fail validation"""
        data = SecurityProfiles.get_profile("production_enhanced")["config"]
        data["security"]["authentication"]["mfa"]["enabled"] = False
        
        # Expired yesterday
        expires = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        data["security"]["overrides"] = {
            "authentication": {
                "mfa": {
                    "reason": "Test Override",
                    "approved_by": "sec_team",
                    "expires": expires # Expired
                }
            }
        }
        
        config = VectorDBConfig(**data)
        warnings = SecurityValidator.validate_config(config)
        
        # Check validation warnings
        blocking = [w for w in warnings if w.blocking]
        # Should have "Override ... has EXPIRED"
        assert len(blocking) > 0
        assert "has EXPIRED" in blocking[0].message

    def test_override_missing_metadata(self):
        """Override without reason/approval should fail"""
        data = SecurityProfiles.get_profile("production_enhanced")["config"]
        data["security"]["overrides"] = {
            "authentication": {
                "mfa": {
                    "enabled": False
                    # Missing reason, approved_by, expires
                }
            }
        }
        
        config = VectorDBConfig(**data)
        warnings = SecurityValidator.validate_config(config)
        
        blocking = [w for w in warnings if w.blocking]
        assert len(blocking) > 0
        assert "missing metadata" in blocking[0].message
