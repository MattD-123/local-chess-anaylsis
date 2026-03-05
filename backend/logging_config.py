from __future__ import annotations

import logging
import logging.config
import uuid
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("-")
        return True


def set_request_id(request_id: str | None = None) -> str:
    value = request_id or str(uuid.uuid4())
    request_id_ctx.set(value)
    return value


def configure_logging(level: str = "INFO") -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": RequestIDFilter}},
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] [req=%(request_id)s] %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                }
            },
            "root": {"level": level, "handlers": ["console"]},
        }
    )
