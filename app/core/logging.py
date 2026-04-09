"""Logging estruturado JSON com redaction básica de dados sensíveis."""

import json
import logging
import re
import sys
from datetime import datetime, timezone


REDACT_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), "[REDACTED_EMAIL]"),
    (re.compile(r"\+?[\d\s\-()]{10,15}"), "[REDACTED_PHONE]"),
    (re.compile(r'"api_key"\s*:\s*"[^"]+"'), '"api_key": "[REDACTED]"'),
    (re.compile(r'"password"\s*:\s*"[^"]+"'), '"password": "[REDACTED]"'),
    (re.compile(r'"secret"\s*:\s*"[^"]+"'), '"secret": "[REDACTED]"'),
    (re.compile(r'"token"\s*:\s*"[^"]+"'), '"token": "[REDACTED]"'),
]


def redact(text: str) -> str:
    for pattern, replacement in REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
        }
        if record.exc_info:
            # Não exibe stacktrace bruto; apenas tipo e mensagem
            exc_type = record.exc_info[0]
            exc_val = record.exc_info[1]
            log_obj["error"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "msg": redact(str(exc_val)),
            }
        for key in ("trace_id", "span_id", "run_id"):
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Silencia loggers externos verbosos
    for noisy in ("httpx", "httpcore", "openai", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
