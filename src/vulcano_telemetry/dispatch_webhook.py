
import json
import logging
import time
import requests

from .core_sqs import get_sqs_client, consume_events
from .exceptions import (SQSConnectionError, WebhookDeliveryError, CorruptedMessageError)
from .webhook_crypto import generate_signature
from botocore.exceptions import BotoCoreError, ClientError


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
    sqs_client = get_sqs_client()

    logger.info(
        "Despachador iniciado. Cola: %s. Destino: %s",
        queue_url,
        target_url,
    )

    while True:
        try:
            events = consume_events(
                sqs_client,
                queue_url,
                wait_time=wait_time,
            )
        except CorruptedMessageError:
            logger.exception("Se recibió un mensaje corrupto de SQS. Se omite.")
            raise

        if not events:
            continue

        logger.info("Recibidos %s eventos de SQS.", len(events))

        for event in events:
            try:
                dispatch_webhook(
                    target_url,
                    secret,
                    event["body"]
                )

                try:
                    sqs_client.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=event["receipt_handle"],
                    )
                except (BotoCoreError, ClientError) as exc:
                    raise SQSConnectionError(
                        f"No se pudo eliminar el mensaje {event['message_id']} de SQS."
                    ) from exc
                logger.info(
                    "Mensaje %s eliminado de SQS tras la entrega.",
                    event["message_id"],
                )

            except WebhookDeliveryError as exc:
                logger.error(
                    "Falló la entrega del mensaje %s: %s",
                    event["message_id"],
                    exc,
                )

            except SQSConnectionError:
                raise

            except Exception:
                logger.exception(
                    "Error inesperado procesando el mensaje %s.",
                    event["message_id"],
                )
