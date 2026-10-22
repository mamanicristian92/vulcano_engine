"""Excepciones semánticas personalizadas para el proyecto Vulcano Pay (SQS + Webhooks)."""

class VulcanoError(Exception):
    """Excepción base para todos los errores del ecosistema Vulcano."""
    pass

class SQSConnectionError(VulcanoError):
    """Lanzada ante fallos de comunicación con AWS SQS / LocalStack."""
    pass

class CorruptedMessageError(VulcanoError):
    """Lanzada cuando el cuerpo del mensaje SQS no es un JSON válido."""
    pass

class WebhookSignatureError(VulcanoError):
    """Lanzada cuando la firma criptográfica HMAC-SHA256 es inválida o ausente."""
    pass

class WebhookTimestampError(VulcanoError):
    """Lanzada cuando el timestamp del Webhook está fuera de la ventana de tolerancia (Replay Attack)."""
    pass

class WebhookDeliveryError(VulcanoError):
    """Lanzada cuando el envío HTTP del Webhook falla tras reintentos."""
    pass