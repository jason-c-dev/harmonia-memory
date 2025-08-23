# Harmonia Memory Storage System Configuration

## Overview

Harmonia uses a flexible, hierarchical configuration system that combines YAML files with environment variable overrides. This approach allows for easy development setup while maintaining security in production environments.

## Configuration Philosophy

- **YAML files** for all non-sensitive configuration options
- **Environment variables** only for secrets and sensitive data
- **Validation** with helpful error messages using Pydantic models
- **Hot-reload** capability for development environments
- **Defaults** for all settings to minimize required configuration

## Configuration Sources

The system loads configuration from multiple sources in this order of precedence:

1. **Default values** (defined in code)
2. **YAML configuration file** (`config/config.yaml`)
3. **Environment variables** (secrets only)
4. **Runtime overrides** (programmatic configuration)

## Main Configuration File

### Location and Structure

**Default path**: `config/config.yaml`

The configuration file is organized into logical sections:

```yaml
# config/config.yaml

# Server Configuration
server:
  host: "0.0.0.0"
  port: 8000
  workers: 1
  cors_origins:
    - "http://localhost:*"
    - "http://127.0.0.1:*"
  request_timeout: 30
  max_request_size: 10485760  # 10MB

# Database Configuration  
database:
  path: "./data/harmonia.db"
  pool_size: 10
  timeout: 30
  backup_interval: 3600      # seconds
  backup_retention: 168      # hours
  vacuum_interval: 86400     # seconds

# Ollama LLM Configuration
ollama:
  host: "http://localhost:11434"
  model: "llama3.2:3b"
  temperature: 0.3
  max_tokens: 500
  timeout: 30
  retry_attempts: 3
  retry_delay: 1
  health_check_interval: 60

# Memory Processing Configuration
memory:
  extraction_enabled: true
  conflict_resolution_strategy: "update"
  temporal_resolution_enabled: true
  default_timezone: "UTC"
  confidence_threshold: 0.7
  max_memory_age_days: 365

# Search Configuration
search:
  max_results: 100
  default_page_size: 10
  fts_enabled: true
  semantic_search_enabled: false
  ranking_algorithm: "bm25"

# Cache Configuration
cache:
  enabled: true
  memory_cache_size: 1000
  search_cache_ttl: 300      # 5 minutes
  user_context_cache_ttl: 3600  # 1 hour

# Logging Configuration
logging:
  level: "INFO"
  format: "structured"
  file:
    enabled: true
    path: "./logs/harmonia.log"
    max_size: "10MB"
    backup_count: 5
    rotation: "size"
  console:
    enabled: true
    level: "INFO"
  structured:
    timestamp_format: "ISO8601"
    include_caller: false

# Security Configuration
security:
  api_key_required: false
  api_keys: []
  rate_limit:
    enabled: true
    requests_per_minute: 100
    requests_per_hour: 1000
  cors:
    allow_credentials: false
    max_age: 86400

# Development Configuration
development:
  debug: false
  auto_reload: false
  profiling_enabled: false
  mock_llm: false

# Monitoring Configuration
monitoring:
  metrics_enabled: true
  health_check_endpoint: "/health"
  metrics_endpoint: "/metrics" 
  prometheus_enabled: false

# Export Configuration
export:
  formats:
    - "json"
    - "csv"
    - "markdown"
    - "text"
  max_export_size: 100000
  compression_enabled: true
```

## Configuration Sections

### Server Configuration

Controls the HTTP server behavior and network settings.

```yaml
server:
  host: "0.0.0.0"              # Bind address (0.0.0.0 for all interfaces)
  port: 8000                   # HTTP port
  workers: 1                   # Number of worker processes
  cors_origins:                # Allowed CORS origins
    - "http://localhost:*"     # Localhost with any port
    - "http://127.0.0.1:*"     # 127.0.0.1 with any port
  request_timeout: 30          # Request timeout in seconds
  max_request_size: 10485760   # Maximum request size in bytes (10MB)
```

**Production Settings**:
```yaml
server:
  host: "0.0.0.0"
  port: 443                    # HTTPS port
  workers: 4                   # More workers for production
  cors_origins:
    - "https://yourdomain.com"
  request_timeout: 60          # Longer timeout for complex operations
  max_request_size: 52428800   # 50MB for larger requests
```

### Database Configuration

SQLite database settings and performance tuning options.

```yaml
database:
  path: "./data/harmonia.db"   # Database file path
  pool_size: 10                # Connection pool size
  timeout: 30                  # Connection timeout in seconds
  backup_interval: 3600        # Automatic backup interval (seconds)
  backup_retention: 168        # Backup retention period (hours)
  vacuum_interval: 86400       # Database vacuum interval (seconds)
```

**Performance Tuning**:
```yaml
database:
  path: "./data/harmonia.db"
  pool_size: 20                # Larger pool for high concurrency
  timeout: 60                  # Longer timeout for complex queries
  backup_interval: 1800        # More frequent backups (30 minutes)
  backup_retention: 336        # Keep backups for 2 weeks
  vacuum_interval: 43200       # Vacuum twice daily
```

### Ollama LLM Configuration

Settings for the Ollama LLM service integration.

```yaml
ollama:
  host: "http://localhost:11434"  # Ollama service URL
  model: "llama3.2:3b"           # Default model to use
  temperature: 0.3               # LLM temperature (0.0-2.0)
  max_tokens: 500                # Maximum tokens in response
  timeout: 30                    # Request timeout in seconds
  retry_attempts: 3              # Number of retry attempts
  retry_delay: 1                 # Base delay between retries
  health_check_interval: 60      # Health check frequency (seconds)
```

**Model Options**:
- `llama3.2:3b`: Fast, good for most tasks (recommended)
- `llama3.1:8b`: Better quality, slower processing
- `llama2:7b`: Alternative model option
- `codellama:7b`: Optimized for code-related content

**Production Settings**:
```yaml
ollama:
  host: "http://ollama.internal:11434"  # Internal service URL
  model: "llama3.1:8b"                  # Higher quality model
  temperature: 0.2                      # Lower temperature for consistency
  max_tokens: 1000                      # More tokens for complex extractions
  timeout: 120                          # Longer timeout for large models
  retry_attempts: 5                     # More retries in production
  retry_delay: 2                        # Longer delay between retries
```

### Memory Processing Configuration

Controls the memory extraction and processing behavior.

```yaml
memory:
  extraction_enabled: true               # Enable memory extraction
  conflict_resolution_strategy: "update" # Default conflict resolution
  temporal_resolution_enabled: true      # Enable temporal processing
  default_timezone: "UTC"               # Default timezone
  confidence_threshold: 0.7             # Minimum confidence for storage
  max_memory_age_days: 365              # Memory retention period (0 = no limit)
```

**Conflict Resolution Strategies**:
- `auto`: Automatic resolution based on confidence
- `update`: Replace old memory with new one
- `merge`: Combine information from both memories
- `version`: Keep both as separate versions
- `skip`: Keep existing memory, ignore new one

**Regional Settings**:
```yaml
memory:
  default_timezone: "America/New_York"  # Eastern Time
  # or
  default_timezone: "Europe/London"     # GMT/BST
  # or  
  default_timezone: "Asia/Tokyo"        # JST
```

### Search Configuration

Full-text search engine settings and performance options.

```yaml
search:
  max_results: 100              # Maximum search results
  default_page_size: 10         # Default pagination size
  fts_enabled: true             # Enable full-text search
  semantic_search_enabled: false  # Future: semantic search
  ranking_algorithm: "bm25"     # Search ranking algorithm
```

**Performance Tuning**:
```yaml
search:
  max_results: 1000             # More results for power users
  default_page_size: 25         # Larger default page size
  fts_enabled: true
  semantic_search_enabled: false
  ranking_algorithm: "bm25"
```

### Cache Configuration

In-memory caching settings for performance optimization.

```yaml
cache:
  enabled: true                 # Enable caching
  memory_cache_size: 1000       # LRU cache size (number of items)
  search_cache_ttl: 300         # Search result cache TTL (seconds)
  user_context_cache_ttl: 3600  # User context cache TTL (seconds)
```

**High-Performance Settings**:
```yaml
cache:
  enabled: true
  memory_cache_size: 5000       # Larger cache for high-traffic
  search_cache_ttl: 600         # Longer cache for search results
  user_context_cache_ttl: 7200  # 2-hour context cache
```

### Logging Configuration

Comprehensive logging settings with multiple output options.

```yaml
logging:
  level: "INFO"                 # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  format: "structured"          # Log format (simple, detailed, structured)
  file:
    enabled: true               # Enable file logging
    path: "./logs/harmonia.log" # Log file path
    max_size: "10MB"           # Maximum log file size
    backup_count: 5             # Number of backup files to keep
    rotation: "size"            # Rotation strategy (size, time)
  console:
    enabled: true               # Enable console logging
    level: "INFO"              # Console log level
  structured:
    timestamp_format: "ISO8601" # Timestamp format
    include_caller: false       # Include caller information
```

**Production Logging**:
```yaml
logging:
  level: "WARNING"              # Less verbose for production
  format: "structured"
  file:
    enabled: true
    path: "/var/log/harmonia/harmonia.log"
    max_size: "50MB"           # Larger files in production
    backup_count: 10           # Keep more backups
    rotation: "size"
  console:
    enabled: false             # Disable console in production
    level: "ERROR"
  structured:
    timestamp_format: "ISO8601"
    include_caller: true       # Include caller for debugging
```

### Security Configuration

Authentication, authorization, and security settings.

```yaml
security:
  api_key_required: false       # Enable API key authentication
  api_keys: []                 # API keys (set via environment variables)
  rate_limit:
    enabled: true              # Enable rate limiting
    requests_per_minute: 100   # Request rate limit
    requests_per_hour: 1000    # Hourly request limit
  cors:
    allow_credentials: false   # Allow credentials in CORS
    max_age: 86400            # CORS max age (seconds)
```

**Production Security**:
```yaml
security:
  api_key_required: true        # Enable authentication
  api_keys: []                 # Set via HARMONIA_API_KEYS environment variable
  rate_limit:
    enabled: true
    requests_per_minute: 50    # Stricter rate limiting
    requests_per_hour: 500
  cors:
    allow_credentials: true    # Allow credentials for authenticated requests
    max_age: 3600             # Shorter cache time
```

## Environment Variables

Environment variables are used exclusively for secrets and sensitive configuration that should not be stored in YAML files.

### Supported Environment Variables

```bash
# API Security (secrets only)
HARMONIA_API_SECRET_KEY=your-secret-key-here-change-me-in-production
HARMONIA_API_KEYS=key1,key2,key3  # Comma-separated list
HARMONIA_API_KEY_REQUIRED=true

# Development Override
HARMONIA_ENV=development  # Special flag for development mode
```

### Setting Up Environment Variables

**Development (.env file)**:
```bash
# Create .env file (never commit this!)
cat > .env << 'EOF'
# Development secrets
HARMONIA_API_KEY_REQUIRED=false
HARMONIA_API_KEYS=dev-key-123,dev-key-456

# Development environment flag
HARMONIA_ENV=development
EOF
```

**Production (system environment)**:
```bash
# Set in production environment
export HARMONIA_API_KEY_REQUIRED=true
export HARMONIA_API_KEYS="prod-key-$(openssl rand -hex 32),backup-key-$(openssl rand -hex 32)"
export HARMONIA_API_SECRET_KEY="$(openssl rand -base64 64)"
```

**Docker Environment**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  harmonia:
    image: harmonia:latest
    environment:
      - HARMONIA_API_KEY_REQUIRED=true
      - HARMONIA_API_KEYS_FILE=/run/secrets/api_keys
    secrets:
      - api_keys
      
secrets:
  api_keys:
    file: ./secrets/api_keys.txt
```

## Configuration Validation

The system validates configuration at startup and provides helpful error messages:

```python
# Example validation errors
ValidationError: Configuration validation failed:
- server.port: Port must be between 1 and 65535
- ollama.temperature: Temperature must be between 0.0 and 2.0  
- memory.confidence_threshold: Confidence threshold must be between 0.0 and 1.0
- logging.level: Log level must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
```

### Custom Validation

```python
from core.config import ConfigLoader

# Load and validate configuration
config_loader = ConfigLoader("config/config.yaml")
config = config_loader.load()

# Check for warnings
warnings = config_loader.validate_config(config)
if warnings:
    for warning in warnings:
        print(f"Warning: {warning}")
```

## Configuration Examples

### Development Environment

```yaml
# config/development.yaml
server:
  host: "127.0.0.1"
  port: 8000
  workers: 1

database:
  path: "./data/dev_harmonia.db"
  pool_size: 5

ollama:
  host: "http://localhost:11434"
  model: "llama3.2:3b"
  timeout: 60

memory:
  confidence_threshold: 0.5  # Lower threshold for development

logging:
  level: "DEBUG"
  console:
    enabled: true
    level: "DEBUG"

development:
  debug: true
  auto_reload: true
  mock_llm: false  # Set to true to mock LLM calls

security:
  api_key_required: false
```

### Production Environment

```yaml
# config/production.yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  cors_origins:
    - "https://yourdomain.com"
    - "https://app.yourdomain.com"

database:
  path: "/data/harmonia/harmonia.db"
  pool_size: 20
  backup_interval: 1800      # 30 minutes
  backup_retention: 720      # 30 days

ollama:
  host: "http://ollama-service:11434"
  model: "llama3.1:8b"
  temperature: 0.2
  timeout: 120
  retry_attempts: 5

memory:
  confidence_threshold: 0.8  # Higher threshold for production
  max_memory_age_days: 730   # 2 years

logging:
  level: "INFO"
  file:
    enabled: true
    path: "/var/log/harmonia/harmonia.log"
    max_size: "100MB"
    backup_count: 20
  console:
    enabled: false

security:
  api_key_required: true     # Enable authentication
  rate_limit:
    requests_per_minute: 60
    requests_per_hour: 600

monitoring:
  metrics_enabled: true
  prometheus_enabled: true
```

### Testing Environment

```yaml
# config/testing.yaml
server:
  host: "127.0.0.1"
  port: 8001
  workers: 1

database:
  path: ":memory:"          # In-memory database for tests
  pool_size: 1

ollama:
  host: "http://localhost:11434"
  model: "llama3.2:3b"
  timeout: 30

memory:
  confidence_threshold: 0.0  # Accept all memories in tests

logging:
  level: "ERROR"            # Minimal logging during tests
  console:
    enabled: false

development:
  mock_llm: true           # Mock LLM calls for consistent tests

security:
  api_key_required: false
  rate_limit:
    enabled: false         # Disable rate limiting for tests
```

## Configuration Management

### Loading Custom Configuration

```python
from core.config import ConfigLoader

# Load custom configuration file
config_loader = ConfigLoader(
    config_path="config/production.yaml",
    env_file=".env.production"
)

config = config_loader.load()
```

### Runtime Configuration Updates

```python
from core.config import get_config, reload_config

# Get current configuration
config = get_config()

# Reload configuration from files (useful for development)
new_config = reload_config()
```

### Configuration in Application Code

```python
from core.config import get_config

def create_database_manager():
    config = get_config()
    
    return DatabaseManager(
        db_path=config.database.path,
        pool_size=config.database.pool_size,
        timeout=config.database.timeout
    )
```

## Best Practices

### 1. Environment-Specific Configuration

Use separate configuration files for different environments:

```
config/
├── config.yaml           # Base configuration
├── development.yaml      # Development overrides
├── production.yaml       # Production settings
├── testing.yaml         # Test environment
└── local.yaml           # Local development (gitignored)
```

### 2. Secret Management

**Never commit secrets to version control:**

```bash
# Add to .gitignore
.env
.env.*
config/local.yaml
config/*-secrets.yaml
```

**Use proper secret management in production:**
```bash
# Use secret management service
HARMONIA_API_KEYS=$(vault kv get -field=api_keys secret/harmonia)
export HARMONIA_API_KEYS
```

### 3. Configuration Validation

Always validate configuration in deployment scripts:

```bash
#!/bin/bash
# deploy.sh

# Validate configuration before deployment
python -c "
from core.config import ConfigLoader
config_loader = ConfigLoader('config/production.yaml')
config = config_loader.load()
warnings = config_loader.validate_config(config)
if warnings:
    print('Configuration warnings:')
    for warning in warnings:
        print(f'  - {warning}')
print('Configuration validation passed')
"

# Continue with deployment...
```

### 4. Configuration Documentation

Document all configuration options:

```yaml
# config/config.yaml
# Configuration for Harmonia Memory Storage System
# 
# This file contains all non-sensitive configuration options.
# Sensitive values (API keys, secrets) should be set via environment variables.
#
# For detailed documentation, see: docs/configuration.md

server:
  # HTTP server bind address
  # Use "0.0.0.0" to bind to all interfaces
  # Use "127.0.0.1" for localhost only
  host: "0.0.0.0"
  
  # HTTP port number (1-65535)
  port: 8000
```

### 5. Monitoring Configuration Changes

Log configuration loading and changes:

```python
import logging

logger = logging.getLogger(__name__)

def load_config():
    try:
        config = ConfigLoader().load()
        logger.info(f"Configuration loaded successfully")
        logger.info(f"Database path: {config.database.path}")
        logger.info(f"Ollama model: {config.ollama.model}")
        logger.info(f"Log level: {config.logging.level}")
        return config
    except Exception as e:
        logger.error(f"Configuration loading failed: {e}")
        raise
```

This comprehensive configuration system provides flexibility, security, and maintainability while supporting both development and production deployment scenarios.