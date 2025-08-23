"""
Configuration management for Harmonia Memory Storage System.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    cors_origins: List[str] = ["http://localhost:*"]
    request_timeout: int = 30
    max_request_size: int = 10485760  # 10MB


class DatabaseConfig(BaseModel):
    """Database configuration."""
    path: str = "./data/harmonia.db"
    pool_size: int = 10
    timeout: int = 30
    backup_interval: int = 3600
    backup_retention: int = 168
    vacuum_interval: int = 86400


class OllamaConfig(BaseModel):
    """Ollama LLM configuration."""
    host: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    temperature: float = 0.3
    max_tokens: int = 500
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1
    health_check_interval: int = 60

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v


class MemoryConfig(BaseModel):
    """Memory processing configuration."""
    extraction_enabled: bool = True
    conflict_resolution_strategy: str = "update"
    temporal_resolution_enabled: bool = True
    default_timezone: str = "UTC"
    confidence_threshold: float = 0.7
    max_memory_age_days: int = 365

    @field_validator('conflict_resolution_strategy')
    @classmethod
    def validate_strategy(cls, v):
        valid_strategies = ['update', 'merge', 'version']
        if v not in valid_strategies:
            raise ValueError(f'Strategy must be one of {valid_strategies}')
        return v

    @field_validator('confidence_threshold')
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence threshold must be between 0.0 and 1.0')
        return v


class SearchConfig(BaseModel):
    """Search configuration."""
    max_results: int = 100
    default_page_size: int = 10
    fts_enabled: bool = True
    semantic_search_enabled: bool = False
    ranking_algorithm: str = "bm25"


class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = True
    memory_cache_size: int = 1000
    search_cache_ttl: int = 300
    user_context_cache_ttl: int = 3600


class LogFileConfig(BaseModel):
    """Log file configuration."""
    enabled: bool = True
    path: str = "./logs/harmonia.log"
    max_size: str = "10MB"
    backup_count: int = 5
    rotation: str = "size"


class LogConsoleConfig(BaseModel):
    """Log console configuration."""
    enabled: bool = True
    level: str = "INFO"


class LogStructuredConfig(BaseModel):
    """Structured logging configuration."""
    timestamp_format: str = "ISO8601"
    include_caller: bool = False


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "structured"
    file: LogFileConfig = LogFileConfig()
    console: LogConsoleConfig = LogConsoleConfig()
    structured: LogStructuredConfig = LogStructuredConfig()

    @field_validator('level')
    @classmethod
    def validate_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of {valid_levels}')
        return v.upper()

    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        valid_formats = ['simple', 'detailed', 'structured']
        if v not in valid_formats:
            raise ValueError(f'Log format must be one of {valid_formats}')
        return v


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    enabled: bool = True
    requests_per_minute: int = 100
    requests_per_hour: int = 1000


class CorsConfig(BaseModel):
    """CORS configuration."""
    allow_credentials: bool = False
    max_age: int = 86400


class SecurityConfig(BaseModel):
    """Security configuration."""
    api_key_required: bool = False
    api_keys: List[str] = []
    rate_limit: RateLimitConfig = RateLimitConfig()
    cors: CorsConfig = CorsConfig()


class DevelopmentConfig(BaseModel):
    """Development configuration."""
    debug: bool = False
    auto_reload: bool = False
    profiling_enabled: bool = False
    mock_llm: bool = False


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    metrics_enabled: bool = True
    health_check_endpoint: str = "/health"
    metrics_endpoint: str = "/metrics"
    prometheus_enabled: bool = False


class ExportConfig(BaseModel):
    """Export configuration."""
    formats: List[str] = ["json", "csv", "markdown", "text"]
    max_export_size: int = 100000
    compression_enabled: bool = True


class Config(BaseModel):
    """Main configuration class."""
    server: ServerConfig = ServerConfig()
    database: DatabaseConfig = DatabaseConfig()
    ollama: OllamaConfig = OllamaConfig()
    memory: MemoryConfig = MemoryConfig()
    search: SearchConfig = SearchConfig()
    cache: CacheConfig = CacheConfig()
    logging: LoggingConfig = LoggingConfig()
    security: SecurityConfig = SecurityConfig()
    development: DevelopmentConfig = DevelopmentConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    export: ExportConfig = ExportConfig()


class ConfigLoader:
    """Configuration loader that handles YAML files and environment variables."""
    
    def __init__(self, config_path: Optional[str] = None, env_file: Optional[str] = None):
        self.config_path = config_path or "config/config.yaml"
        self.env_file = env_file or ".env"
        self._config_cache: Optional[Config] = None
    
    def load(self, force_reload: bool = False) -> Config:
        """Load configuration from YAML and environment variables."""
        if self._config_cache is not None and not force_reload:
            return self._config_cache
        
        # Load environment variables from .env file if it exists
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
        
        # Load YAML configuration
        config_data = self._load_yaml_config()
        
        # Apply environment variable overrides
        config_data = self._apply_env_overrides(config_data)
        
        # Validate and create config object
        try:
            self._config_cache = Config(**config_data)
            return self._config_cache
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path(self.config_path)
        
        if not config_path.exists():
            # Return default configuration if file doesn't exist
            return {}
        
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load configuration file: {e}")
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides for secrets only."""
        # Only support environment variables for secrets that shouldn't be in config.yaml
        env_mappings = {
            # Security - Secrets only
            'HARMONIA_API_SECRET_KEY': ('security', 'api_secret_key'),
            'HARMONIA_API_KEYS': ('security', 'api_keys'),  # Comma-separated list
            'HARMONIA_API_KEY_REQUIRED': ('security', 'api_key_required'),
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Special handling for API keys list
                if env_var == 'HARMONIA_API_KEYS':
                    value = [key.strip() for key in env_value.split(',') if key.strip()]
                else:
                    value = self._convert_env_value(env_value)
                self._set_nested_value(config_data, config_path, value)
        
        return config_data
    
    def _set_nested_value(self, data: Dict[str, Any], path: tuple, value: Any) -> None:
        """Set a nested value in the configuration dictionary."""
        current = data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # Integer conversion
        try:
            if '.' not in value:
                return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def validate_config(self, config: Config) -> List[str]:
        """Validate configuration and return list of warnings/errors."""
        warnings = []
        
        # Check database path directory exists
        db_path = Path(config.database.path)
        if not db_path.parent.exists():
            warnings.append(f"Database directory does not exist: {db_path.parent}")
        
        # Check log directory exists
        log_path = Path(config.logging.file.path)
        if config.logging.file.enabled and not log_path.parent.exists():
            warnings.append(f"Log directory does not exist: {log_path.parent}")
        
        # Validate Ollama configuration
        if not config.ollama.host.startswith(('http://', 'https://')):
            warnings.append("Ollama host should start with http:// or https://")
        
        # Check API keys if required
        if config.security.api_key_required and not config.security.api_keys:
            warnings.append("API key authentication is enabled but no keys are configured")
        
        return warnings
    
    def reload(self) -> Config:
        """Reload configuration from files."""
        return self.load(force_reload=True)


# Global configuration instance
_config_loader = ConfigLoader()


def get_config() -> Config:
    """Get the current configuration."""
    return _config_loader.load()


def reload_config() -> Config:
    """Reload configuration from files."""
    return _config_loader.reload()


def validate_config() -> List[str]:
    """Validate current configuration."""
    config = get_config()
    return _config_loader.validate_config(config)


# For backwards compatibility
config = get_config()