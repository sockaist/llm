from typing import Dict, List, Any
from datetime import datetime
from llm_backend.server.vector_server.config.security_config import VectorDBConfig

class ValidationWarning:
    def __init__(self, severity: str, message: str, recommendation: str, blocking: bool = False):
        self.severity = severity # critical, high, medium, low
        self.message = message
        self.recommendation = recommendation
        self.blocking = blocking
    
    def to_dict(self):
        return {
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "blocking": self.blocking
        }

class SecurityValidator:
    """
    Validates VectorDB Security Configuration.
    Enforces 'Guardrails' for overrides and minimum tier requirements.
    """
    
    @staticmethod
    def validate_config(config: VectorDBConfig) -> List[ValidationWarning]:
        warnings = []
        sec = config.security
        tier = sec.tier
        overrides = sec.overrides
        
        # 1. Tier Requirements Validation
        if tier >= 1: # Basic Production
             if not sec.authentication.enabled:
                 warnings.append(ValidationWarning(
                     "critical", "Authentication DISABLED in Production Tier 1+", 
                     "Enable authentication or downgrade to Tier 0", blocking=True
                 ))
             if not sec.encryption.at_rest:
                 warnings.append(ValidationWarning(
                     "high", "Encryption At-Rest DISABLED in Production",
                     "Enable at-rest encryption"
                 ))

        if tier >= 2: # Enhanced Production
             # MFA Check
             if not (sec.authentication.mfa and sec.authentication.mfa.get("enabled")):
                 # Check override
                 if "authentication" in overrides and "mfa" in overrides["authentication"]:
                      pass # Will validate override explicitly later
                 else:
                      warnings.append(ValidationWarning(
                          "high", "MFA required for Tier 2+", 
                          "Enable MFA or add an authorized override", blocking=True
                      ))
             
             # Audit Log Integrity
             if not (sec.audit_logging.integrity and sec.audit_logging.integrity.get("enabled")):
                  warnings.append(ValidationWarning(
                      "medium", "Log Integrity required for Tier 2+",
                      "Enable integrity checks (hash chaining)"
                  ))

        # 2. Override Validation ("Guardrails")
        # Structure of override: overrides['feature_name']['sub_feature'] = { ... metadata ... }
        # Actually Schema defines overrides as Dict[str, Dict[str, Any]]
        # Example: overrides['authentication'] = {'mfa': {'enabled': False, 'reason': ..., 'expires': ...}}
        
        for feature, sub_overrides in overrides.items():
            for sub_feature, details in sub_overrides.items():
                 # Valid override must have metadata
                 required_fields = ["reason", "approved_by", "expires"]
                 missing = [f for f in required_fields if f not in details]
                 
                 if missing:
                      warnings.append(ValidationWarning(
                          "critical", f"Override for {feature}.{sub_feature} missing metadata: {missing}",
                          "Add reason, approved_by, and expires fields", blocking=True
                      ))
                      continue
                 
                 # Expiration Check
                 try:
                     expires_str = details["expires"]
                     # Supports ISO format YYYY-MM-DD
                     expires_date = datetime.fromisoformat(expires_str)
                     if expires_date < datetime.now():
                          warnings.append(ValidationWarning(
                              "critical", f"Override for {feature}.{sub_feature} has EXPIRED ({expires_str})",
                              "Renew override or remove it to enforce security", blocking=True
                          ))
                 except ValueError:
                      warnings.append(ValidationWarning(
                          "high", f"Invalid expiration date format for {feature}.{sub_feature}",
                          "Use YYYY-MM-DD format", blocking=True
                      ))

        # 3. Development Mode Sanity Check
        if config.environment == "development" and tier > 0:
             warnings.append(ValidationWarning(
                 "low", f"Running High Security Tier ({tier}) in Development environment",
                 "Consider using Tier 0 for faster iteration"
             ))

        return warnings
