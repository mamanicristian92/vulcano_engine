"""Validadores sanitizadores declarativos para la CLI de Vulcano."""

import argparse
import re
from urllib.parse import urlparse

def parse_queue_name(value: str) -> str:
    """Valida que el nombre de la cola cumpla con el patrón vulcano-<nombre>-queue."""
    pattern = r"^vulcano-[a-z0-9-]+-queue$"
    if not re.match(pattern, value):
        raise argparse.ArgumentTypeError(
            f"Nombre de cola inválido '{value}'. Debe seguir el patrón 'vulcano-<nombre>-queue'."
        )
    return value

def parse_wait_time(value: str) -> int:
    """Sanitiza el tiempo de Long Polling para SQS (1 a 20 segundos)."""
    try:
        val = int(value)
        if not (1 <= val <= 20):
            raise ValueError()
        return val
    except ValueError:
        raise argparse.ArgumentTypeError(f"WaitTimeSeconds inválido '{value}'. Debe ser entre 1 y 20 s.")

def parse_webhook_url(value: str) -> str:
    """Valida que la URL del webhook tenga esquema HTTP o HTTPS válido."""
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise argparse.ArgumentTypeError(f"URL de Webhook inválida '{value}'. Debe ser HTTP/HTTPS.")
    return value

def parse_secret_key(value: str) -> str:
    """Valida la longitud mínima de la clave secreta HMAC."""
    if len(value) < 16:
        raise argparse.ArgumentTypeError("La clave secreta HMAC debe tener al menos 16 caracteres.")
    return value