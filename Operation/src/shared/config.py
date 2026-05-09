"""Configuration loader from YAML files"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    def __init__(self):
        self.data = {}
    
    def load(self, env: str = None):
        """Load configuration from YAML files"""
        if env is None:
            env = os.getenv("ENVIRONMENT", "dev")
        
        config_dir = Path("config")
        
        # Load default config
        default_path = config_dir / "default.yaml"
        if default_path.exists():
            with open(default_path) as f:
                self.data = yaml.safe_load(f) or {}
        
        # Load environment specific config
        env_path = config_dir / f"{env}.yaml"
        if env_path.exists():
            with open(env_path) as f:
                env_config = yaml.safe_load(f) or {}
                self._deep_merge(self.data, env_config)
        
        # Load domain configs
        for config_file in config_dir.glob("*_config.yaml"):
            if config_file.name != "default.yaml":
                with open(config_file) as f:
                    domain_config = yaml.safe_load(f) or {}
                    domain_name = config_file.stem.replace("_config", "")
                    self.data[domain_name] = domain_config
        
        return self.data
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge override into base dict"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key"""
        keys = key.split(".")
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default


# Global config instance
_config = None


def get_config() -> Config:
    """Get global config instance"""
    global _config
    if _config is None:
        _config = Config()
        _config.load()
    return _config


def load_config() -> Dict:
    """Load and return configuration"""
    return get_config().data
