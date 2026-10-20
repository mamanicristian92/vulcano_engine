"""Engine de observabilidad con formato JSON, QueueHandler y compresión Gzip."""

import gzip
import json
import logging
import logging.handlers
import os
import queue
import shutil
from datetime import datetime, timezone

class AsyncJSONFormatter(logging.Formatter):
    """Formateador JSON estructurado conforme a ISO 8601 UTC."""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "process_id": record.process,
            "thread_name": record.threadName,
            "taskName": getattr(record, "taskName", None),
        }
        
class AsyncJSONFormatter(logging.Formatter):
    """Formateador JSON estructurado conforme a ISO 8601 UTC."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "process": record.process,
            "threadName": record.threadName,
            "taskName": getattr(record, "taskName", None),
        }

        # Identificadores de trazabilidad, si están disponibles.
        for field in ("TraceId", "MessageId", "WebhookId"):
            value = getattr(record, field, None)
            if value is not None:
                log_data[field] = value

        # Incorporar metadatos adicionales enviados mediante extra.
        standard_fields = set(logging.makeLogRecord({}).__dict__)
        for key, value in record.__dict__.items():
            if key not in standard_fields and key not in log_data:
                log_data[key] = value
        # Registrar información de excepciones.
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


def gzip_namer(default_name: str) -> str:
    return default_name + ".gz"

def gzip_rotator(source: str, dest: str) -> None:
    with open(source, "rb") as f_in:
        with gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(source)

def setup_vulcano_logging(log_filename: str = "vulcano_events.log"):
    """Configura el pipeline de logging no bloqueante mediante QueueHandler y QueueListener."""
    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)

    file_handler = logging.handlers.RotatingFileHandler(
        log_filename, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(AsyncJSONFormatter())
    file_handler.namer = gzip_namer
    file_handler.rotator = gzip_rotator

    listener = logging.handlers.QueueListener(log_queue, file_handler)
    listener.start()

    logger = logging.getLogger("vulcano_engine")
    logger.setLevel(logging.INFO)
    logger.addHandler(queue_handler)
    logger.listener = listener
    return logger