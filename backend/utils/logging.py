import logging
import sys
import json
import re
import contextvars
from datetime import datetime
from config.config import settings

# Global ContextVar for thread/async-safe request_id tracing
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

# Centralized secret redaction patterns
SECRET_PATTERNS = [
    (re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"), "AIzaSy***REDACTED***"),
    (re.compile(r"mongodb\+srv://([^:]+):([^@]+)@"), r"mongodb+srv://****:****@"),
    (re.compile(r"mongodb://([^:]+):([^@]+)@"), r"mongodb://****:****@"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.\+/=]+"), "Bearer ***REDACTED***"),
    (re.compile(r"(?i)(password|secret|api_key|apikey|token|uri)\s*=\s*['\"][^'\"]+['\"]"), r"\1=***REDACTED***"),
    (re.compile(r"(?i)(password|secret|api_key|apikey|token|uri)\s*:\s*['\"][^'\"]+['\"]"), r"\1:***REDACTED***"),
]

def redact_secrets(val: str) -> str:
    """Helper to redact sensitive patterns from log strings."""
    if not isinstance(val, str):
        return val
    for pattern, replacement in SECRET_PATTERNS:
        val = pattern.sub(replacement, val)
    return val


class RequestIdFilter(logging.Filter):
    """Filter that dynamically injects request_id from contextvars into records."""
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs JSON formatted logs with redaction applied."""
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "line": record.lineno,
            "request_id": getattr(record, "request_id", ""),
        }
        
        # Parse payload
        if isinstance(record.msg, dict):
            for k, v in record.msg.items():
                if isinstance(v, str):
                    log_obj[k] = redact_secrets(v)
                else:
                    log_obj[k] = v
        else:
            log_obj["event"] = redact_secrets(record.getMessage())
            
        # Exception details logging
        if record.exc_info:
            log_obj["exception"] = redact_secrets(self.formatException(record.exc_info))
            
        return json.dumps(log_obj)


def setup_logging():
    """Setup logging configuration for the FastAPI application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Reset existing handlers to prevent duplicate basicConfig logs
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    handler.addFilter(RequestIdFilter())

    logging.basicConfig(
        level=log_level,
        handlers=[handler]
    )

    logger = logging.getLogger("customer_support_backend")
    logger.info(f"Logging initialized with level: {logging.getLevelName(log_level)}")
    return logger


logger = setup_logging()
