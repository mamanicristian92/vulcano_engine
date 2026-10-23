"""Módulo de seguridad criptográfica HMAC-SHA256 para Webhooks."""

import hmac
import hashlib
import time
from .exceptions import WebhookSignatureError, WebhookTimestampError

def generate_signature(secret: str, timestamp: int, payload_bytes: bytes) -> str:
    """Genera la firma HMAC-SHA256 en formato hex sobre timestamp.payload_bytes."""
    to_sign = f"{timestamp}.".encode("utf-8") + payload_bytes
    return hmac.new(secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()

def verify_signature(secret: str, header_value: str, payload_bytes: bytes, tolerance_sec: int = 300) -> bool:
    """
    Verifica la cabecera X-Webhook-Signature (formato: t=timestamp,v1=signature).
    Protege contra Replay Attacks (timestamp) y Timing Attacks (hmac.compare_digest).
    """
    if not header_value or "t=" not in header_value or "v1=" not in header_value:
        raise WebhookSignatureError("Cabecera X-Webhook-Signature malformada o ausente.")

    parts = dict(item.split("=") for item in header_value.split(","))
    timestamp = int(parts.get("t", 0))
    received_sig = parts.get("v1", "")

    # 1. Mitigación de Replay Attacks (Verificación de Tolerancia Temporal)
    current_time = int(time.time())
    if abs(current_time - timestamp) > tolerance_sec:
        raise WebhookTimestampError(f"Timestamp fuera de tolerancia ({abs(current_time - timestamp)}s > {tolerance_sec}s).")

    # 2. Mitigación de Timing Attacks (Comparación en Tiempo Constante)
    expected_sig = generate_signature(secret, timestamp, payload_bytes)
    if not hmac.compare_digest(expected_sig, received_sig):
        raise WebhookSignatureError("Firma HMAC-SHA256 no coincide.")

    return True
