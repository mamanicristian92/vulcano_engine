import os
import json
import logging
import time
import requests

from .core_sqs import get_sqs_client, receive_events, delete_event
from .exceptions import (SQSConnectionError, WebhookDeliveryError, CorruptedMessageError)
from .webhook_crypto import generate_signature


logger = logging.getLogger("vulcano_engine")


def dispatch_webhook(target_url: str, secret: str, payload_dict: dict,) -> None:
    """Firma un evento con HMAC-SHA256 y lo envía por HTTP POST."""
    payload_bytes = json.dumps(
        payload_dict,
        separators=(",", ":"),
    ).encode("utf-8")

    timestamp = int(time.time())
    signature = generate_signature(secret, timestamp, payload_bytes)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"t={timestamp},v1={signature}",
    }

    try:
        response = requests.post(
            target_url,
            data=payload_bytes,
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise WebhookDeliveryError(
            f"No se pudo entregar el webhook a {target_url}."
        ) from exc

    logger.info(
        "Webhook entregado a %s. Código HTTP: %s",
        target_url,
        response.status_code,
    )


def run_dispatcher(queue_url: str, wait_time: int, target_url: str, secret: str,) -> None:
    """Consume eventos de SQS y los despacha a su destino HTTP."""
    sqs_endpoint_url = os.environ.get("SQS_ENDPOINT_URL", "http://localhost:4566")
    sqs_client = get_sqs_client(sqs_endpoint_url)

    logger.info(
        "Despachador iniciado. Cola: %s. Destino: %s",
        queue_url,
        target_url,
    )

    while True:
        try:
            events = receive_events(
                sqs_client,
                queue_url,
                wait_time=wait_time,
            )
        except CorruptedMessageError:
            logger.exception(
                "Error al consumir eventos: se detectó un mensaje "
                "corrupto en SQS. Se propaga la excepción."
            )
            raise

        if not events:
            continue
        logger.info("Recibidos %s eventos de SQS.", len(events))

        for event in events:
            message_id = event["message_id"]

            try:
                dispatch_webhook(
                    target_url,
                    secret,
                    event["body"],
                )

            except WebhookDeliveryError as exc:
                logger.error(
                    "Fallo en la entrega HTTP del mensaje %s: %s",
                    message_id,
                    exc,
                )
                continue

            except Exception:
                logger.exception(
                    "Error inesperado al enviar el mensaje %s.",
                    message_id,
                )
                continue

            try:
                delete_event(
                    sqs_client,
                    queue_url,
                    event["receipt_handle"],
                    message_id,
                )

            except SQSConnectionError:
                logger.exception(
                    "El webhook del mensaje %s fue entregado correctamente, pero no se pudo eliminar de SQS. Se propaga la excepción.",
                    message_id,
                )
                raise
