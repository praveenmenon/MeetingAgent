"""
Centralized logging configuration for Meeting Agent
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "api_provider"):
            log_data["api_provider"] = record.api_provider
        if hasattr(record, "execution_time"):
            log_data["execution_time"] = record.execution_time

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class LoggingConfig:
    """Central logging configuration manager."""

    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    RICH_FORMAT = "%(message)s"

    @staticmethod
    def setup_logging(
        level: str = "INFO",
        log_file: Optional[str] = None,
        use_rich: bool = True,
        use_structured: bool = False,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        extra_loggers: Optional[Dict[str, str]] = None,
    ) -> logging.Logger:
        """
        Setup centralized logging configuration.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (optional)
            use_rich: Use Rich handler for colored console output
            use_structured: Use structured JSON logging
            max_bytes: Maximum size of log files before rotation
            backup_count: Number of backup log files to keep
            extra_loggers: Additional loggers with their levels

        Returns:
            Configured root logger
        """

        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Set root level
        root_logger.setLevel(getattr(logging, level.upper()))

        # Console handler
        if use_rich:
            console = Console(stderr=True)
            console_handler = RichHandler(
                console=console, show_time=False, show_path=False, markup=True
            )
            console_formatter = logging.Formatter(LoggingConfig.RICH_FORMAT)
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            if use_structured:
                console_formatter = StructuredFormatter()
            else:
                console_formatter = logging.Formatter(LoggingConfig.DEFAULT_FORMAT)

        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(console_handler)

        # File handler (if specified)
        if log_file:
            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )

            if use_structured:
                file_formatter = StructuredFormatter()
            else:
                file_formatter = logging.Formatter(LoggingConfig.DEFAULT_FORMAT)

            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)  # Always log everything to file
            root_logger.addHandler(file_handler)

        # Configure specific loggers
        LoggingConfig._configure_third_party_loggers()

        # Configure additional loggers if specified
        if extra_loggers:
            for logger_name, logger_level in extra_loggers.items():
                logger = logging.getLogger(logger_name)
                logger.setLevel(getattr(logging, logger_level.upper()))

        return root_logger

    @staticmethod
    def _configure_third_party_loggers():
        """Configure third-party library loggers."""

        # Suppress verbose third-party loggers
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("anthropic").setLevel(logging.WARNING)
        logging.getLogger("redis").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

        # Keep our loggers visible
        logging.getLogger("meeting_agent").setLevel(logging.INFO)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger with the given name."""
        return logging.getLogger(name)

    @staticmethod
    def setup_production_logging(log_dir: str = "logs") -> logging.Logger:
        """Setup production-ready logging configuration."""

        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        # Production log files
        app_log = os.path.join(log_dir, "meeting-agent.log")
        error_log = os.path.join(log_dir, "meeting-agent-error.log")

        # Setup main logger
        root_logger = LoggingConfig.setup_logging(
            level="INFO",
            log_file=app_log,
            use_rich=False,  # No colors in production
            use_structured=True,  # Structured logging for parsing
            max_bytes=50 * 1024 * 1024,  # 50MB files
            backup_count=10,
        )

        # Add separate error log handler
        error_handler = logging.handlers.RotatingFileHandler(
            error_log, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)

        # Configure production-specific loggers
        extra_loggers = {
            "meeting_agent.rate_limiter": "WARNING",
            "meeting_agent.ai_client": "INFO",
            "meeting_agent.notion_client": "INFO",
            "meeting_agent.worker": "INFO",
            "meeting_agent.main": "INFO",
        }

        for logger_name, level in extra_loggers.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(getattr(logging, level))

        return root_logger

    @staticmethod
    def setup_development_logging() -> logging.Logger:
        """Setup development-friendly logging configuration."""

        return LoggingConfig.setup_logging(
            level="DEBUG",
            log_file="logs/meeting-agent-dev.log",
            use_rich=True,  # Rich colors for development
            use_structured=False,  # Human-readable format
            extra_loggers={
                "meeting_agent": "DEBUG",
                "meeting_agent.rate_limiter": "DEBUG",
                "meeting_agent.ai_client": "DEBUG",
            },
        )

    @staticmethod
    def setup_testing_logging() -> logging.Logger:
        """Setup logging for testing environment."""

        return LoggingConfig.setup_logging(
            level="WARNING",  # Reduce noise during testing
            use_rich=False,
            use_structured=False,
        )


class LoggingMixin:
    """Mixin class to add logging capabilities to any class."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            )
        return self._logger

    def log_execution_time(self, operation: str, start_time: float, end_time: float):
        """Log execution time for an operation."""
        execution_time = end_time - start_time
        self.logger.info(
            f"Operation '{operation}' completed",
            extra={"execution_time": execution_time, "operation": operation},
        )

    def log_api_call(
        self,
        provider: str,
        operation: str,
        success: bool,
        execution_time: Optional[float] = None,
    ):
        """Log API call details."""
        level = logging.INFO if success else logging.ERROR
        message = f"{provider} {operation} {'succeeded' if success else 'failed'}"

        extra = {"api_provider": provider, "operation": operation, "success": success}
        if execution_time is not None:
            extra["execution_time"] = execution_time

        self.logger.log(level, message, extra=extra)

    def log_user_action(
        self, user_id: str, action: str, details: Optional[Dict[str, Any]] = None
    ):
        """Log user action."""
        extra = {"user_id": user_id, "action": action}
        if details:
            extra.update(details)

        self.logger.info(f"User {user_id} performed action: {action}", extra=extra)


def configure_logging():
    """Configure logging based on environment."""

    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return LoggingConfig.setup_production_logging()
    elif env == "testing":
        return LoggingConfig.setup_testing_logging()
    else:
        return LoggingConfig.setup_development_logging()


# Context managers for request tracing
class RequestContext:
    """Context manager for request tracing."""

    def __init__(self, request_id: str, user_id: Optional[str] = None):
        self.request_id = request_id
        self.user_id = user_id
        self.old_factory = None

    def __enter__(self):
        # Store old record factory
        self.old_factory = logging.getLogRecordFactory()

        # Set new factory that adds request context
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.request_id = self.request_id
            if self.user_id:
                record.user_id = self.user_id
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old factory
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


# Performance monitoring decorator
def log_performance(operation_name: str = None):
    """Decorator to log function execution time."""

    def decorator(func):
        import functools
        import time

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = logging.getLogger(func.__module__)

            op_name = operation_name or f"{func.__name__}"

            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time

                logger.info(
                    f"Operation '{op_name}' completed successfully",
                    extra={
                        "operation": op_name,
                        "execution_time": execution_time,
                        "success": True,
                    },
                )
                return result

            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time

                logger.error(
                    f"Operation '{op_name}' failed: {str(e)}",
                    extra={
                        "operation": op_name,
                        "execution_time": execution_time,
                        "success": False,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


# Initialize logging when module is imported
if not logging.getLogger().handlers:
    configure_logging()
