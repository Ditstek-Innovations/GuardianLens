"""Structured JSON logging — TRD 15.2, BACKEND_CODING_RULES 17.

stdlib logging with a JSON formatter (structlog is deliberately not a
dependency). Request context — trace_id, tenant, user — travels in
contextvars so every log line within a request carries it without any
caller passing it around.

What must never appear here is longer than what must: no passwords, no JWT
or refresh-token material, no connection strings with credentials, no
camera credentials, no evidence bytes, and no per-person activity
aggregate — a "user X reviewed 47 events today" log line is an individual
productivity metric, prohibited in logs exactly as in the product
(TRD 15.3). Audit records go to the audit_log table, never to a log file
(TRD 15.5); this module is the operational aid, not the record.
"""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any

SERVICE_NAME = "control-plane"

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
tenant_var: contextvars.ContextVar[str] = contextvars.ContextVar("tenant", default="")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="")


class JsonFormatter(logging.Formatter):
    """One JSON object per line, TRD 15.2 field names."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "channel": getattr(record, "channel", "application"),
            "service": SERVICE_NAME,
            "event": record.getMessage(),
        }
        if trace_id_var.get():
            entry["trace_id"] = trace_id_var.get()
        if tenant_var.get():
            entry["tenant"] = tenant_var.get()
        if user_id_var.get():
            entry["user_id"] = user_id_var.get()
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            entry.update(extra)
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = record.exc_info[0].__name__
        return json.dumps(entry, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotent root configuration. Safe to call from app factory and CLI.

    ADDS the JSON handler rather than replacing the handler list: other
    parties legitimately attach root handlers (pytest's capture does, and
    removing them silently breaks observability elsewhere — the exact
    failure mode BACKEND_CODING_RULES 16 warns about, applied to logs).
    """
    root = logging.getLogger()
    if any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger, event: str, level: int = logging.INFO, **context: Any
) -> None:
    """Log a structured event with extra context fields."""
    logger.log(level, event, extra={"context": context})
