from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field

# ==========================================
# Sub-Models
# ==========================================


class AuthenticationConfig(BaseModel):
    enabled: bool = True
    method: str = "api_key"  # api_key, jwt, mfa

    # JWT / MFA specifics
    jwt: Dict[str, Any] = Field(default_factory=dict)
    mfa: Dict[str, Any] = Field(default_factory=dict)
    api_key: Dict[str, Any] = Field(default_factory=dict)


class AuthorizationConfig(BaseModel):
    enabled: bool = True
    method: str = "rbac"  # rbac, abac, hybrid
    roles: List[str] = Field(default_factory=list)
    abac: Dict[str, Any] = Field(default_factory=dict)


class RateLimitConfig(BaseModel):
    enabled: bool = True
    strategy: str = "simple"  # simple, advanced, adaptive
    limits: Dict[str, Any] = Field(default_factory=dict)


class AuditConfig(BaseModel):
    enabled: bool = True
    level: str = "standard"
    tiered_storage: Dict[str, Any] = Field(default_factory=dict)
    integrity: Dict[str, Any] = Field(default_factory=dict)


class EncryptionConfig(BaseModel):
    at_rest: bool = True
    in_transit: bool = True
    field_level: Dict[str, Any] = Field(default_factory=dict)


class DefenseConfig(BaseModel):
    injection_detection: bool = True
    anomaly_detection: bool = False
    business_logic: Dict[str, Any] = Field(default_factory=dict)


class ComplianceConfig(BaseModel):
    gdpr: Union[bool, str] = False
    hipaa: Union[bool, str] = False
    soc2: Union[bool, str] = False


# ==========================================
# Main Security Config
# ==========================================


class SecuritySection(BaseModel):
    tier: int = 1
    authentication: AuthenticationConfig = Field(default_factory=AuthenticationConfig)
    authorization: AuthorizationConfig = Field(default_factory=AuthorizationConfig)
    rate_limiting: RateLimitConfig = Field(default_factory=RateLimitConfig)
    audit_logging: AuditConfig = Field(default_factory=AuditConfig)
    encryption: EncryptionConfig = Field(default_factory=EncryptionConfig)
    defense: DefenseConfig = Field(default_factory=DefenseConfig)

    # Overrides for temporary exceptions
    overrides: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class VectorDBConfig(BaseModel):
    environment: str = "production"
    security: SecuritySection = Field(default_factory=SecuritySection)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    warnings: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)


# Global Config Instance (Loaded at runtime)
current_config: Optional[VectorDBConfig] = None


def load_configuration(path: str = "vectordb.yaml") -> VectorDBConfig:
    import yaml
    import os

    global current_config

    # Default to Basic Profile if no file exists
    if not os.path.exists(path):
        from llm_backend.server.vector_server.config.security_profiles import (
            SecurityProfiles,
        )

        print(f"Config file {path} not found. Loading default Tier 1 profile.")
        default_data = SecurityProfiles.get_profile("production_basic")["config"]
        config = VectorDBConfig(**default_data)
    else:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        config = VectorDBConfig(**data)

    current_config = config
    return current_config
