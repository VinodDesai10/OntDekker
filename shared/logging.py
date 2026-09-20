import logging
import sys
import json
import contextvars
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Context variables to store Request-ID and Correlation-ID per thread/async task
request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("correlation_id", default=None)

class StructuredJsonFormatter(logging.Formatter):
    def __init__(self, service_name: str, **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": request_id_ctx.get(),
            "correlation_id": correlation_id_ctx.get(),
        }

        # Include exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Include extra attributes supplied via extra={}
        if hasattr(record, "extra_data"):
            log_record["extra"] = record.extra_data

        return json.dumps(log_record)

def setup_logging(service_name: str, log_level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    
    # Clean up existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        
    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredJsonFormatter(service_name=service_name)
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Silence noise from uvicorn or databases if needed
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
