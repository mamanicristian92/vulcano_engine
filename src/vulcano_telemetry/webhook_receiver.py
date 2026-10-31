"""
Recepción y autenticación de webhooks con FastAPI y Amazon SQS.

Valida las firmas HMAC-SHA256 y los timestamps de las solicitudes
entrantes antes de publicar los eventos autenticados en SQS.
Compatible con LocalStack para el entorno de desarrollo.
"""
import json
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, status
from .webhook_crypto import verify_signature
from .core_sqs import get_sqs_client, send_event
from .exceptions import WebhookSignatureError, WebhookTimestampError, SQSConnectionError

# Cargamos variables de entorno e inicializamos el logger.
load_dotenv()
logger = logging.getLogger("vulcano_engine")

# Asignamos la API.
app = FastAPI(title="Vulcano Webhook Receiver")

# Obtenemos y validamos el secreto para autenticar los webhooks.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not WEBHOOK_SECRET:
    raise RuntimeError(
        "Falta configurar WEBHOOK_SECRET en el entorno."
    )

QUEUE_NAME = "vulcano-events-queue"

SQS_ENDPOINT_URL = os.getenv(
    "SQS_ENDPOINT_URL",
    "http://localhost:4566",
)

sqs_client = get_sqs_client(SQS_ENDPOINT_URL)

QUEUE_URL = sqs_client.get_queue_url(
    QueueName=QUEUE_NAME
)["QueueUrl"]

@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)

async def receive_webhook(request: Request):
    """Autentica, valida y publica eventos webhook en una cola SQS."""

    # Obtenemos el cuerpo original y la firma enviada en la solicitud.
    raw_bytes = await request.body()
    signature_header = request.headers.get("X-Webhook-Signature", "")

    # Verificamos la autenticidad del webhook antes de procesar su contenido.
    try:
        verify_signature(WEBHOOK_SECRET, signature_header, raw_bytes)
    except (
        WebhookSignatureError,
        WebhookTimestampError,
        ValueError,
        TypeError,
    ) as err:
        logger.warning(
            "Rechazado Webhook no autenticado: %s",
            err,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación del webhook fallida.",
        ) from err

    # Interpretamos el cuerpo de la solicitud como JSON.
    try:
        payload = await request.json()
    except (
        json.JSONDecodeError,
        UnicodeDecodeError
    ) as err:
        logger.warning(
            "Rechazado webhook con contenido JSON inválido: %s",
            err,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cuerpo de la solicitud no contiene un JSON válido.",
        ) from err

    # Publicamos el evento autenticado en la cola de SQS.
    try:
        msg_id = send_event(sqs_client, QUEUE_URL, payload)
    except SQSConnectionError as err:
        logger.error("Error al publicar el evento en SQS: %s", err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible procesar el evento temporalmente.",
        ) from err

    # Registramos la publicación exitosa y devolvemos el identificador del mensaje.
    logger.info(
        "Webhook verificado y encolado exitosamente en SQS. MessageId: %s",
        msg_id,
    )
    return {"status": "accepted", "message_id": msg_id}
