"""
Centralized configuration management for Meeting Agent
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class NotionConfig(BaseModel):
    """Notion-specific configuration."""

    token: str = Field(..., min_length=1, description="Notion integration token")
    database_id: str = Field(..., min_length=1, description="Meetings database ID")
    tasks_database_id: str = Field(..., min_length=1, description="Tasks database ID")
    api_version: str = Field(default="2022-06-28", description="Notion API version")
    timeout: int = Field(
        default=30, ge=5, le=120, description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum retry attempts"
    )

    @validator("token")
    def validate_token(cls, v):
        """Validate Notion token format."""
        if not (v.startswith("secret_") or v.startswith("ntn_")):
            raise ValueError('Notion token must start with "secret_" or "ntn_"')
        return v


class AIConfig(BaseModel):
    """AI services configuration."""

    openai_api_key: str = Field(..., min_length=1, description="OpenAI API key")
    anthropic_api_key: str = Field(..., min_length=1, description="Anthropic API key")
    openai_org_id: Optional[str] = Field(
        default=None, description="OpenAI organization ID"
    )
    default_openai_model: str = Field(
        default="gpt-4o-mini", description="Default OpenAI model"
    )
    default_anthropic_model: str = Field(
        default="claude-3-5-sonnet-20240620", description="Default Anthropic model"
    )
    max_tokens_default: int = Field(
        default=1000, ge=1, le=8000, description="Default max tokens"
    )
    temperature_default: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Default temperature"
    )
    timeout: int = Field(default=60, ge=5, le=300, description="API request timeout")

    @validator("openai_api_key")
    def validate_openai_key(cls, v):
        """Validate OpenAI API key format."""
        if not v.startswith("sk-"):
            raise ValueError('OpenAI API key must start with "sk-"')
        return v


class MemoryConfig(BaseModel):
    """Memory service configuration."""

    api_key: Optional[str] = Field(default=None, description="Mem0 API key")
    user_id: str = Field(default="default_user", description="Default user ID")
    enabled: bool = Field(default=False, description="Enable memory features")
    api_url: str = Field(default="https://api.mem0.ai", description="Mem0 API URL")
    timeout: int = Field(default=30, description="Request timeout")

    @validator("enabled", pre=True)
    def validate_enabled(cls, v, values):
        """Enable memory only if API key is provided."""
        if isinstance(v, str):
            v = v.lower() in ("true", "1", "yes", "on")
        return bool(v and values.get("api_key"))


class RedisConfig(BaseModel):
    """Redis configuration for async processing."""

    url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    max_connections: int = Field(
        default=20, ge=1, le=100, description="Max connection pool size"
    )
    timeout: int = Field(default=30, ge=1, le=300, description="Connection timeout")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    socket_keepalive: bool = Field(default=True, description="Enable socket keepalive")

    @validator("url")
    def validate_redis_url(cls, v):
        """Validate Redis URL format."""
        if not v.startswith(("redis://", "rediss://", "unix://")):
            raise ValueError(
                "Redis URL must start with redis://, rediss://, or unix://"
            )
        return v


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    max_retries: int = Field(
        default=5, ge=0, le=20, description="Maximum retry attempts"
    )
    base_delay: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Base delay in seconds"
    )
    max_delay: float = Field(
        default=60.0, ge=1.0, le=300.0, description="Maximum delay in seconds"
    )
    exponential_base: float = Field(
        default=2.0, ge=1.1, le=5.0, description="Exponential backoff base"
    )
    jitter: bool = Field(default=True, description="Enable jitter")
    jitter_max: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Maximum jitter fraction"
    )
    rate_limit_delay: float = Field(
        default=60.0, ge=1.0, le=3600.0, description="Rate limit delay"
    )
    quota_exceeded_delay: float = Field(
        default=3600.0, ge=60.0, le=86400.0, description="Quota exceeded delay"
    )


class AsyncConfig(BaseModel):
    """Async processing configuration."""

    enabled: bool = Field(default=False, description="Enable async processing")
    queue_name: str = Field(default="meeting_jobs", description="Job queue name")
    max_queue_size: int = Field(
        default=1000, ge=10, le=10000, description="Maximum queue size"
    )
    worker_timeout: int = Field(
        default=300, ge=30, le=3600, description="Worker timeout"
    )
    job_timeout: int = Field(default=3600, ge=60, le=86400, description="Job timeout")
    max_chunk_size: int = Field(
        default=4000, ge=1000, le=10000, description="Max chunk size for transcripts"
    )
    chunk_overlap: int = Field(
        default=200, ge=50, le=1000, description="Chunk overlap size"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_file_size: int = Field(
        default=10485760,
        ge=1048576,
        le=104857600,
        description="Max log file size (10MB)",
    )
    backup_count: int = Field(
        default=5, ge=1, le=50, description="Number of backup log files"
    )
    use_rich: bool = Field(default=True, description="Use Rich console output")
    use_structured: bool = Field(
        default=False, description="Use structured JSON logging"
    )

    @validator("level")
    def validate_level(cls, v):
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Logging level must be one of: {valid_levels}")
        return v.upper()


class ApplicationConfig(BaseSettings):
    """Main application configuration."""

    # Basic settings
    app_name: str = Field(default="Meeting Agent", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(
        default="development",
        description="Environment (development, production, testing)",
    )
    debug: bool = Field(default=False, description="Debug mode")

    # User settings
    default_assignee: str = Field(
        default="Meeting Agent User", description="Default task assignee"
    )
    timezone: str = Field(default="UTC", description="Default timezone")

    # Component configurations
    notion: NotionConfig
    ai: AIConfig
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    async_config: AsyncConfig = Field(default_factory=AsyncConfig)
    logging_config: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = ["development", "production", "testing", "staging"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    def is_testing(self) -> bool:
        """Check if running in testing."""
        return self.environment == "testing"


class ConfigManager:
    """Configuration manager with validation and caching."""

    _instance: Optional[ApplicationConfig] = None
    _config_file: Optional[str] = None

    @classmethod
    def load_config(
        cls, config_file: Optional[str] = None, force_reload: bool = False
    ) -> ApplicationConfig:
        """
        Load and validate configuration.

        Args:
            config_file: Path to configuration file (.env)
            force_reload: Force reload even if already loaded

        Returns:
            ApplicationConfig instance
        """

        if cls._instance is not None and not force_reload:
            return cls._instance

        # Load environment file if specified
        if config_file:
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
            load_dotenv(config_file, override=True)
            cls._config_file = config_file
        else:
            # Try to find .env file in common locations
            env_files = [
                ".env",
                "config/.env",
                os.path.expanduser("~/.meeting-agent/.env"),
            ]

            for env_file in env_files:
                if os.path.exists(env_file):
                    load_dotenv(env_file)
                    cls._config_file = env_file
                    break

        try:
            # Create configuration with environment variable mapping
            config_data = cls._build_config_dict()
            cls._instance = ApplicationConfig(**config_data)

            # Validate configuration
            cls._validate_config(cls._instance)

            return cls._instance

        except Exception as e:
            logging.error(f"Configuration loading failed: {e}")
            raise

    @classmethod
    def _build_config_dict(cls) -> Dict[str, Any]:
        """Build configuration dictionary from environment variables."""

        config_data = {}

        # Basic settings
        config_data["app_name"] = os.getenv("APP_NAME", "Meeting Agent")
        config_data["version"] = os.getenv("APP_VERSION", "1.0.0")
        config_data["environment"] = os.getenv("ENVIRONMENT", "development")
        config_data["debug"] = os.getenv("DEBUG", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        config_data["default_assignee"] = os.getenv(
            "DEFAULT_ASSIGNEE", "Meeting Agent User"
        )
        config_data["timezone"] = os.getenv("TIMEZONE", "UTC")

        # Notion configuration
        config_data["notion"] = {
            "token": os.getenv("NOTION_TOKEN", ""),
            "database_id": os.getenv("DATABASE_ID", ""),
            "tasks_database_id": os.getenv("TASKS_DATABASE_ID", ""),
            "api_version": os.getenv("NOTION_API_VERSION", "2022-06-28"),
            "timeout": int(os.getenv("NOTION_TIMEOUT", "30")),
            "max_retries": int(os.getenv("NOTION_MAX_RETRIES", "3")),
        }

        # AI configuration
        config_data["ai"] = {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            "openai_org_id": os.getenv("OPENAI_ORG_ID"),
            "default_openai_model": os.getenv("DEFAULT_OPENAI_MODEL", "gpt-4o-mini"),
            "default_anthropic_model": os.getenv(
                "DEFAULT_ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"
            ),
            "max_tokens_default": int(os.getenv("AI_MAX_TOKENS_DEFAULT", "1000")),
            "temperature_default": float(os.getenv("AI_TEMPERATURE_DEFAULT", "0.7")),
            "timeout": int(os.getenv("AI_TIMEOUT", "60")),
        }

        # Memory configuration
        config_data["memory"] = {
            "api_key": os.getenv("MEM0_API_KEY"),
            "user_id": os.getenv("DEFAULT_USER_ID", "default_user"),
            "enabled": os.getenv("MEMORY_ENABLED", "false").lower()
            in ("true", "1", "yes"),
            "api_url": os.getenv("MEM0_API_URL", "https://api.mem0.ai"),
            "timeout": int(os.getenv("MEM0_TIMEOUT", "30")),
        }

        # Redis configuration
        config_data["redis"] = {
            "url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "db": int(os.getenv("REDIS_DB", "0")),
            "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
            "timeout": int(os.getenv("REDIS_TIMEOUT", "30")),
            "retry_on_timeout": os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower()
            in ("true", "1", "yes"),
            "socket_keepalive": os.getenv("REDIS_SOCKET_KEEPALIVE", "true").lower()
            in ("true", "1", "yes"),
        }

        # Rate limit configuration
        config_data["rate_limit"] = {
            "max_retries": int(os.getenv("RATE_LIMIT_MAX_RETRIES", "5")),
            "base_delay": float(os.getenv("RATE_LIMIT_BASE_DELAY", "1.0")),
            "max_delay": float(os.getenv("RATE_LIMIT_MAX_DELAY", "60.0")),
            "exponential_base": float(os.getenv("RATE_LIMIT_EXPONENTIAL_BASE", "2.0")),
            "jitter": os.getenv("RATE_LIMIT_JITTER", "true").lower()
            in ("true", "1", "yes"),
            "jitter_max": float(os.getenv("RATE_LIMIT_JITTER_MAX", "0.1")),
            "rate_limit_delay": float(os.getenv("RATE_LIMIT_RATE_LIMIT_DELAY", "60.0")),
            "quota_exceeded_delay": float(
                os.getenv("RATE_LIMIT_QUOTA_EXCEEDED_DELAY", "3600.0")
            ),
        }

        # Async configuration
        config_data["async_config"] = {
            "enabled": os.getenv("ENABLE_ASYNC_PROCESSING", "false").lower()
            in ("true", "1", "yes"),
            "queue_name": os.getenv("ASYNC_QUEUE_NAME", "meeting_jobs"),
            "max_queue_size": int(os.getenv("ASYNC_MAX_QUEUE_SIZE", "1000")),
            "worker_timeout": int(os.getenv("ASYNC_WORKER_TIMEOUT", "300")),
            "job_timeout": int(os.getenv("ASYNC_JOB_TIMEOUT", "3600")),
            "max_chunk_size": int(os.getenv("ASYNC_MAX_CHUNK_SIZE", "4000")),
            "chunk_overlap": int(os.getenv("ASYNC_CHUNK_OVERLAP", "200")),
        }

        # Logging configuration
        config_data["logging_config"] = {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "format": os.getenv(
                "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            "file_path": os.getenv("LOG_FILE"),
            "max_file_size": int(os.getenv("LOG_MAX_FILE_SIZE", "10485760")),
            "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
            "use_rich": os.getenv("LOG_USE_RICH", "true").lower()
            in ("true", "1", "yes"),
            "use_structured": os.getenv("LOG_USE_STRUCTURED", "false").lower()
            in ("true", "1", "yes"),
        }

        return config_data

    @classmethod
    def _validate_config(cls, config: ApplicationConfig):
        """Validate configuration completeness and consistency."""

        errors = []

        # Check required API keys
        if not config.notion.token:
            errors.append("NOTION_TOKEN is required")
        if not config.notion.database_id:
            errors.append("DATABASE_ID is required")
        if not config.notion.tasks_database_id:
            errors.append("TASKS_DATABASE_ID is required")
        if not config.ai.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        if not config.ai.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required")

        # Check memory configuration consistency
        if config.memory.enabled and not config.memory.api_key:
            errors.append("MEM0_API_KEY is required when memory is enabled")

        # Check async configuration consistency
        if config.async_config.enabled:
            try:
                import redis

                # Try to connect to Redis if async is enabled
                r = redis.from_url(config.redis.url)
                r.ping()
            except ImportError:
                errors.append("redis package is required for async processing")
            except Exception as e:
                errors.append(f"Cannot connect to Redis: {e}")

        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

    @classmethod
    def get_config(cls) -> ApplicationConfig:
        """Get current configuration instance."""
        if cls._instance is None:
            return cls.load_config()
        return cls._instance

    @classmethod
    def reload_config(cls, config_file: Optional[str] = None) -> ApplicationConfig:
        """Reload configuration."""
        return cls.load_config(config_file, force_reload=True)


# Legacy compatibility functions (for existing code)
def validate_config():
    """Legacy function for configuration validation."""
    try:
        ConfigManager.load_config()
    except Exception as e:
        logging.error(f"Configuration validation failed: {e}")
        raise


def get_config() -> ApplicationConfig:
    """Get current configuration."""
    return ConfigManager.get_config()


# Initialize clients based on configuration
def get_openai_client():
    """Get configured OpenAI client."""
    config = get_config()
    from openai import OpenAI

    client = OpenAI(
        api_key=config.ai.openai_api_key,
        organization=config.ai.openai_org_id,
        timeout=config.ai.timeout,
    )
    return client


def get_anthropic_client():
    """Get configured Anthropic client."""
    config = get_config()
    from anthropic import Anthropic

    client = Anthropic(api_key=config.ai.anthropic_api_key, timeout=config.ai.timeout)
    return client


# Export configured clients for backward compatibility
def _get_legacy_exports():
    """Get legacy exports with proper error handling."""
    try:
        config = get_config()
        return {
            "OPENAI_CLIENT": get_openai_client(),
            "ANTHROPIC_CLIENT": get_anthropic_client(),
            "NOTION_TOKEN": config.notion.token,
            "DATABASE_ID": config.notion.database_id,
            "TASKS_DATABASE_ID": config.notion.tasks_database_id,
            "DEFAULT_ASSIGNEE": config.default_assignee,
            "MEM0_API_KEY": config.memory.api_key,
            "DEFAULT_USER_ID": config.memory.user_id,
            "MEMORY_ENABLED": config.memory.enabled,
            "NOTION_HEADERS": {
                "Authorization": f"Bearer {config.notion.token}",
                "Content-Type": "application/json",
                "Notion-Version": config.notion.api_version,
            },
        }
    except Exception:
        # Fallback for testing or when config is not available
        return {
            "OPENAI_CLIENT": None,
            "ANTHROPIC_CLIENT": None,
            "NOTION_TOKEN": "",
            "DATABASE_ID": "",
            "TASKS_DATABASE_ID": "",
            "DEFAULT_ASSIGNEE": "Meeting Agent User",
            "MEM0_API_KEY": None,
            "DEFAULT_USER_ID": "default_user",
            "MEMORY_ENABLED": False,
            "NOTION_HEADERS": {
                "Authorization": "Bearer ",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
        }


# Initialize legacy exports lazily
_exports = None


def _ensure_exports():
    """Ensure legacy exports are initialized."""
    global _exports
    if _exports is None:
        _exports = _get_legacy_exports()


# Lazy initialization of exports
def __getattr__(name):
    """Provide legacy exports via module attribute access."""
    _ensure_exports()
    if name in _exports:
        return _exports[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Initialize commonly used exports for immediate access
try:
    _ensure_exports()
    OPENAI_CLIENT = _exports["OPENAI_CLIENT"]
    ANTHROPIC_CLIENT = _exports["ANTHROPIC_CLIENT"]
    NOTION_TOKEN = _exports["NOTION_TOKEN"]
    DATABASE_ID = _exports["DATABASE_ID"]
    TASKS_DATABASE_ID = _exports["TASKS_DATABASE_ID"]
    DEFAULT_ASSIGNEE = _exports["DEFAULT_ASSIGNEE"]
    MEM0_API_KEY = _exports["MEM0_API_KEY"]
    DEFAULT_USER_ID = _exports["DEFAULT_USER_ID"]
    MEMORY_ENABLED = _exports["MEMORY_ENABLED"]
    NOTION_HEADERS = _exports["NOTION_HEADERS"]
except Exception:
    # Set fallback values if initialization fails
    OPENAI_CLIENT = None
    ANTHROPIC_CLIENT = None
    NOTION_TOKEN = ""
    DATABASE_ID = ""
    TASKS_DATABASE_ID = ""
    DEFAULT_ASSIGNEE = "Meeting Agent User"
    MEM0_API_KEY = None
    DEFAULT_USER_ID = "default_user"
    MEMORY_ENABLED = False
    NOTION_HEADERS = {
        "Authorization": "Bearer ",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
