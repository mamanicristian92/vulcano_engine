"""Recepción y autenticación de webhooks con FastAPI y Amazon SQS.

Valida las firmas HMAC-SHA256 y los timestamps de las solicitudes
entrantes antes de publicar los eventos autenticados en SQS.
Compatible con LocalStack para el entorno de desarrollo.
"""
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, status
from .webhook_crypto import verify_signature
from .core_sqs import get_sqs_client, produce_event
from .exceptions import WebhookSignatureError, WebhookTimestampError

load_dotenv()
logger = logging.getLogger("vulcano_engine")
app = FastAPI(title="Vulcano Webhook Receiver")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
QUEUE_NAME = "vulcano-events-queue"

SQS_ENDPOINT_URL = os.getenv(
    "SQS_ENDPOINT_URL",
    "http://localhost:4566",
)

sqs_client = get_sqs_client(SQS_ENDPOINT_URL)

QUEUE_URL = sqs_client.get_queue_url(
    QueueName=QUEUE_NAME
)["QueueUrl"]


# Impide iniciar el receptor sin el secreto necesario para validar firmas.

if not WEBHOOK_SECRET:
    raise RuntimeError(
        "Falta configurar WEBHOOK_SECRET en el entorno."
    )

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
    msg_id = produce_event(sqs_client, QUEUE_URL, payload)
    
    logger.info(f"Webhook verificado y encolado exitosamente en SQS. MessageId: {msg_id}")
    return {"status": "accepted", "message_id": msg_id}
