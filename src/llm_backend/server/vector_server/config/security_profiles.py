from typing import Dict, Any, List
# This file defines the Pre-Configured Security Profiles

class SecurityProfiles:
    """
    Tiered Security Profiles for 'Progressive Security Enhancement'
    """
    
    PROFILES = {
        "development": {
            "tier": 0,
            "description": "Local development, no security",
            "use_case": "Learning, Testing, Prototyping",
            "warnings": [
                "🔓 Authentication DISABLED",
                "⚠️ Warning: All users have admin access",
                "⚠️ Do NOT expose to internet"
            ],
            "config": {
                "environment": "development",
                "security": {
                    "tier": 0,
                    "authentication": {
                        "enabled": False,
                        "api_key": {} # Empty
                    },
                    "authorization": {
                        "enabled": False
                    },
                    "rate_limiting": {
                        "enabled": False
                    },
                    "audit_logging": {
                        "enabled": True, # Keep logging habit
                        "level": "basic"
                    },
                    "encryption": {
                        "at_rest": False,
                        "in_transit": False
                    },
                    "defense": {
                        "injection_detection": False,
                        "anomaly_detection": False
                    }
                },
                "compliance": {
                    "gdpr": False,
                    "hipaa": False,
                    "soc2": False
                }
            }
        },
        
        "production_basic": {
            "tier": 1,
            "description": "Production ready, basic security",
            "use_case": "Small teams, Internal apps",
            "config": {
                "environment": "production",
                "security": {
                    "tier": 1,
                    "authentication": {
                        "enabled": True,
                        "method": "api_key",
                        "api_key": {
                            "length": 32,
                            "expiration": "90d"
                        }
                    },
                    "authorization": {
                        "enabled": True,
                        "method": "rbac",
                        "roles": ["admin", "developer", "viewer"]
                    },
                    "rate_limiting": {
                        "enabled": True,
                        "strategy": "simple",
                        "limits": {
                            "rps": 10,
                            "rpm": 100
                        }
                    },
                    "audit_logging": {
                        "enabled": True,
                        "level": "standard",
                         "tiered_storage": {
                            "tier1": {"retention": "90d"}
                        }
                    },
                    "encryption": {
                        "at_rest": True,
                        "in_transit": True
                    },
                    "defense": {
                        "injection_detection": True,
                        "anomaly_detection": False
                    }
                },
                "compliance": {
                    "gdpr": "partial",
                    "hipaa": False,
                    "soc2": False
                }
            }
        },
        
        "production_enhanced": {
            "tier": 2,
            "description": "Enterprise ready, strong security",
            "use_case": "SaaS, Multi-tenant, Customer data",
            "config": {
                "environment": "production",
                "security": {
                    "tier": 2,
                    "authentication": {
                        "enabled": True,
                        "method": "jwt",
                        "mfa": {
                            "enabled": True,
                            "methods": ["totp", "sms"]
                        }
                    },
                    "authorization": {
                        "enabled": True,
                        "method": "hybrid", # RBAC + ABAC
                        "roles": ["admin", "engineer", "analyst", "viewer"],
                        "abac": {"enabled": True}
                    },
                    "rate_limiting": {
                        "enabled": True,
                        "strategy": "advanced", # Redis
                        "limits": {
                            "tier_based": True,
                            "free": {"qps": 10},
                            "pro": {"qps": 100}
                        }
                    },
                    "audit_logging": {
                        "enabled": True,
                        "level": "comprehensive",
                        "tiered_storage": {
                            "tier1": {"retention": "7y"},
                            "tier2": {"retention": "1y"}
                        },
                        "integrity": {"enabled": True} # Hash Chaining
                    },
                    "encryption": {
                        "at_rest": True,
                        "in_transit": True,
                        "field_level": {
                            "enabled": True,
                            "fields": ["email", "user_id"]
                        }
                    },
                    "defense": {
                        "injection_detection": True,
                        "anomaly_detection": True, # Z-Score
                        "business_logic": {
                            "export_quota": {"enabled": True}
                        }
                    }
                },
                "compliance": {
                    "gdpr": True,
                    "soc2": True,
                    "hipaa": "partial"
                }
            }
        },
        
        "production_maximum": {
            "tier": 3,
            "description": "Mission critical, maximum security",
            "use_case": "Healthcare, Finance, Government",
            "config": {
                "environment": "production",
                "security": {
                    "tier": 3,
                    "authentication": {
                        "enabled": True,
                        "method": "multi_factor",
                        "mfa": {"enabled": True},
                        "sso": {"enabled": True} # Enterprise SSO
                    },
                    "authorization": {
                        "enabled": True,
                        "method": "policy_engine", # OPA
                    },
                    "audit_logging": {
                        "enabled": True,
                        "level": "maximum",
                        "integrity": {"blockchain": True}
                    },
                    "encryption": {
                        "at_rest": True,
                        "searchable": True # Encrypted Search
                    },
                    "defense": {
                        "injection_detection": True,
                        "anomaly_detection": True,
                        "threat_intelligence": True
                    }
                },
                "compliance": {
                    "gdpr": True,
                    "hipaa": True, # Full
                    "soc2": True,
                    "iso27001": True
                }
            }
        }
    }

    @classmethod
    def get_profile(cls, name: str) -> Dict[str, Any]:
        """Get security profile by name"""
        return cls.PROFILES.get(name)
    
    @classmethod
    def list_profiles(cls) -> List[Dict[str, Any]]:
        """List all available profiles"""
        return [
            {
                "name": name,
                "tier": profile["tier"],
                "description": profile["description"],
                "use_case": profile["use_case"]
            }
            for name, profile in cls.PROFILES.items()
        ]
