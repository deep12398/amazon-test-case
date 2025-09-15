"""Structured logging configuration for Amazon Tracker."""

import json
import logging
import logging.config
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def configure_logging(
    service_name: str,
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """Configure structured logging.

    Args:
        service_name: Service name
        log_level: Log level
        log_format: Log format (json/text)
        log_file: Log file path
        enable_console: Enable console logging
        enable_file: Enable file logging
    """

    # Create log directory
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {},
        "handlers": {},
        "loggers": {},
        "root": {"level": log_level, "handlers": []},
    }

    # Log formatter
    if log_format == "json":
        config["formatters"]["json"] = {"()": JSONFormatter, "service": service_name}
        formatter_name = "json"
    else:
        config["formatters"]["detailed"] = {
            "format": "[{asctime}] {levelname:8s} {name}: {message}",
            "style": "{",
        }
        formatter_name = "detailed"

    # Log handlers
    if enable_console:
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": formatter_name,
            "stream": "ext://sys.stdout",
        }
        config["root"]["handlers"].append("console")

    if enable_file and log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": formatter_name,
            "filename": log_file,
            "maxBytes": 50 * 1024 * 1024,  # 50MB
            "backupCount": 5,
        }
        config["root"]["handlers"].append("file")

    # Application logger
    config["loggers"]["amazon_tracker"] = {
        "level": log_level,
        "handlers": config["root"]["handlers"],
        "propagate": False,
    }

    # Apply configuration
    logging.config.dictConfig(config)


class JSONFormatter(logging.Formatter):
    """JSON log formatter."""

    def __init__(self, service: str = "unknown"):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""

        # Basic fields
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Exception info
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Extra fields
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            }:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class StructuredLogger:
    """Structured logger wrapper."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context = {}

    def set_context(self, **kwargs):
        """Set logging context."""
        self._context.update(kwargs)

    def clear_context(self):
        """Clear logging context."""
        self._context.clear()

    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log with context."""
        context = {**self._context, **kwargs}
        self.logger.log(level, message, extra=context)

    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._log_with_context(logging.ERROR, message, exc_info=True, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Get structured logger instance."""
    return StructuredLogger(name)


class LoggingMixin:
    """Logging mixin class."""

    @property
    def logger(self) -> StructuredLogger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


class RequestLoggingMiddleware:
    """Request logging middleware."""

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("request")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = None
        start_time = None

        async def receive_wrapper():
            return await receive()

        async def send_wrapper(message):
            nonlocal start_time

            if message["type"] == "http.response.start":
                start_time = datetime.utcnow()

                # Log request start
                self.logger.info(
                    "Request started",
                    request_id=request_id,
                    method=scope["method"],
                    path=scope["path"],
                    query_string=scope.get("query_string", b"").decode(),
                )

            elif message["type"] == "http.response.body":
                if start_time:
                    duration = (datetime.utcnow() - start_time).total_seconds()

                    # Log request completion
                    self.logger.info(
                        "Request completed",
                        request_id=request_id,
                        method=scope["method"],
                        path=scope["path"],
                        status_code=message.get("status", 200),
                        duration=duration,
                    )

            await send(message)

        # Extract request ID from headers
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                request_id = value.decode()
                break

        await self.app(scope, receive_wrapper, send_wrapper)


def setup_request_logging(app):
    """Setup request logging middleware."""
    return RequestLoggingMiddleware(app)


# Utility filters
class HealthCheckFilter(logging.Filter):
    """Filter out health check logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Skip health check endpoints
        if hasattr(record, "path"):
            if record.path in ["/health", "/ready", "/metrics"]:
                return False
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from logs."""

    SENSITIVE_KEYS = {"password", "secret", "token", "key", "auth", "credential"}

    def filter(self, record: logging.LogRecord) -> bool:
        # Mask sensitive extra data
        if hasattr(record, "extra"):
            self._mask_sensitive_data(record.extra)

        # Mask message content
        record.msg = self._mask_message(str(record.msg))

        return True

    def _mask_sensitive_data(self, data: dict[str, Any]):
        """Mask sensitive data in dictionary."""
        if isinstance(data, dict):
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                    data[key] = "***MASKED***"
                elif isinstance(value, dict):
                    self._mask_sensitive_data(value)

    def _mask_message(self, message: str) -> str:
        """Mask sensitive data in message."""
        import re

        # JWT token
        message = re.sub(
            r"Bearer\s+[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+",
            "Bearer ***MASKED***",
            message,
        )

        # API keys (32+ character hex strings)
        message = re.sub(
            r"\b[a-f0-9]{32,}\b", "***MASKED***", message, flags=re.IGNORECASE
        )

        return message
