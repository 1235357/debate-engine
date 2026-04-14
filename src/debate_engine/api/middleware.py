"""Structured JSON logging middleware for DebateEngine.

Provides request/response logging with unique request IDs, latency tracking,
and optional cost attribution. Uses Python's built-in logging module with a
custom JSON formatter.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("debate_engine.access")


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include any extra fields attached to the record
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "relativeCreated",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "pathname",
            "filename",
            "module",
            "thread",
            "threadName",
            "process",
            "processName",
            "levelname",
            "levelno",
            "message",
            "msecs",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_entry[key] = value

        # Include exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every HTTP request with structured JSON.

    Adds the following to each log entry:
    - request_id: UUID for correlating request/response
    - method: HTTP method
    - path: URL path
    - query_params: Query string parameters (if any)
    - status_code: HTTP response status code
    - latency_ms: Request processing time in milliseconds
    - client_ip: Client IP address
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        # Attach request_id to the request state for downstream use
        request.state.request_id = request_id

        # Process the request
        response: Response | None = None
        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "latency_ms": round(latency_ms, 2),
                    "client_ip": request.client.host if request.client else "unknown",
                    "error": str(exc),
                },
            )
            raise

        latency_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params) if request.query_params else None,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        # Inject request_id into response header
        response.headers["X-Request-ID"] = request_id

        return response


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging with the JSON formatter.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Set debate_engine loggers to the same level
    logging.getLogger("debate_engine").setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("debate_engine.access").setLevel(
        getattr(logging, level.upper(), logging.INFO)
    )
