import os
import yaml
from typing import Any, Dict, Optional
import logging
from dotenv import dotenv_values, load_dotenv

# Load system environment variables from .env file immediately
load_dotenv()

class ConfigObject:
    """
    Helper class to access configuration dictionary as object attributes.
    Example: config.server.port instead of config['server']['port']
    """
    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __getattr__(self, key: str) -> Any:
        if key in self._data:
            val = self._data[key]
            if isinstance(val, dict):
                return ConfigObject(val)
            return val
        raise AttributeError(f"Config key not found: {key}")
    
    def __repr__(self) -> str:
        return str(self._data)
        
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def dict(self) -> Dict[str, Any]:
        return self._data

class Config:
    """
    Configuration Loader for VectorDB v2.0
    Hierarchy:
    1. defaults.yaml
    2. {env}.yaml (development/production)
    3. .env file (Secrets)
    4. Environment Variables (OS)
    """
    
    _instance = None
    _logger = logging.getLogger("vectordb.config")
    
    @classmethod
    def load(cls, env: Optional[str] = None) -> ConfigObject:
        """
        Load configuration based on environment.
        """
        if cls._instance:
             # In a real app we might want to reload, but for now singleton behavior for performance
             pass

        # Determine environment
        if not env:
            env = os.getenv("VECTORDB_ENV", "development")
            
        project_root = os.getcwd() # Assumption: running from root
        config_dir = os.path.join(project_root, "config")
        
        # 1. Load Defaults
        defaults_path = os.path.join(config_dir, "defaults.yaml")
        if not os.path.exists(defaults_path):
            cls._logger.error(f"Default config not found at {defaults_path}")
            raise FileNotFoundError(f"Default config not found at {defaults_path}")
            
        cls._logger.debug(f"Loading defaults from {defaults_path}")
        with open(defaults_path, "r") as f:
            config_dict = yaml.safe_load(f)
            
        # 2. Load Environment Specific Config
        env_path = os.path.join(config_dir, f"{env}.yaml")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                env_config = yaml.safe_load(f)
                if env_config:
                    cls._deep_update(config_dict, env_config)
        
        # 3. Load Secrets from .env (and overwrite critical keys)
        # load_dotenv() is already called, but we might want to map specific keys manually
        # to ensure structure.
        
        # Only strict set of overrides allowed from Env Vars to prevent pollution
        env_overrides = {
            "VECTORDB_API_KEY": ("vectordb", "api_key"),
            "VECTORDB_HOST": ("vectordb", "host"),
            "VECTORDB_PORT": ("vectordb", "port"),
            "VECTORDB_ENGINE": ("vectordb", "engine"),
            "APP_ENV": ("app", "env"),
            "LOG_LEVEL": ("logging", "level"),
            "QDRANT_API_KEY": ("vectordb", "api_key"),
            "VECTORDB_MASTER_KEY": ("security", "api_key")
        }
        
        for env_var, path in env_overrides.items():
            val = os.getenv(env_var)
            if val:
                # Navigate and set
                current = config_dict
                for key in path[:-1]:
                    current = current.setdefault(key, {})
                
                # Type conversion for Port/Ints
                if val.isdigit():
                    val = int(val)
                elif val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                    
                current[path[-1]] = val
                
        cls._instance = ConfigObject(config_dict)
        return cls._instance

    @staticmethod
    def _deep_update(base_dict: Dict, update_dict: Dict):
        """Recursively update dictionary."""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                Config._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
