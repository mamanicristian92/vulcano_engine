"""Recepción y autenticación de webhooks con FastAPI y Amazon SQS.

Valida las firmas HMAC-SHA256 y los timestamps de las solicitudes
entrantes antes de publicar los eventos autenticados en SQS.
Compatible con LocalStack para el entorno de desarrollo.
"""

import os
import logging
from .logging_engine import setup_vulcano_logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, status
from .webhook_crypto import verify_signature
from .core_sqs import get_sqs_client, send_events
from .exceptions import WebhookSignatureError, WebhookTimestampError

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
    
    raw_bytes = await request.body()
    signature_header = request.headers.get("X-Webhook-Signature", "")

    try:
        verify_signature(WEBHOOK_SECRET, signature_header, raw_bytes)
    except (WebhookSignatureError, WebhookTimestampError) as err:
        logger.warning(f"Rechazado Webhook no autenticado: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    payload = await request.json()
    msg_id = send_events(sqs_client, QUEUE_URL, payload)
    
    logger.info(
        "Webhook verificado y encolado exitosamente en SQS. MessageId: %s",
        msg_id,
    )
    return {"status": "accepted", "message_id": msg_id}
