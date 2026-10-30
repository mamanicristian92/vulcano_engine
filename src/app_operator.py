import os
import argparse
import uvicorn
import time
import requests

from dotenv import load_dotenv
from vulcano_telemetry.webhook_receiver import app
from vulcano_telemetry.sanitizer import parse_queue_name, parse_wait_time, parse_webhook_url, parse_secret_key
from vulcano_telemetry.core_sqs import get_sqs_client, produce_event
from vulcano_telemetry.webhook_crypto import generate_signature
from vulcano_telemetry.logging_engine import setup_vulcano_logging
from vulcano_telemetry.dispatch_webhook import run_dispatcher
from vulcano_telemetry.exceptions import (SQSConnectionError, WebhookSignatureError, WebhookTimestampError, WebhookDeliveryError, CorruptedMessageError)
from botocore.exceptions import BotoCoreError, ClientError

load_dotenv()  # Cargar variables de entorno desde .env

logger = setup_vulcano_logging()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="VulcanoCLI", description="Motor de Eventos SQS y Webhooks HMAC")

    subparsers = parser.add_subparsers(dest="comando", required=True,)

    # Productor de eventos SQS
    producer_parser = subparsers.add_parser("produce-sqs", help="Publicar eventos en la cola SQS",)
    producer_parser.add_argument("-q", "--queue", type=parse_queue_name, default="vulcano-events-queue", help="Nombre de la cola SQS",)

    # Receptor de Webhooks
    receiver_parser = subparsers.add_parser("start-receiver", help="Iniciar el receptor de Webhooks HTTP",)
    receiver_parser.add_argument("--host", default="127.0.0.1", help="Dirección de escucha del receptor",)
    receiver_parser.add_argument("--port", type=int, default=8000, help="Puerto HTTP del receptor",)

    # Despachador de eventos
    dispatcher_parser = subparsers.add_parser("start-dispatcher", help="Consumir eventos de SQS y enviar a Webhooks",)
    dispatcher_parser.add_argument("-q", "--queue", type=parse_queue_name, default="vulcano-events-queue", help="Nombre de la cola SQS",)
    dispatcher_parser.add_argument("-w", "--wait-time", type=parse_wait_time, default=10, help="Tiempo de Long Polling (1-20s)",)
    dispatcher_parser.add_argument("--url", type=parse_webhook_url, default="http://localhost:8000/webhook", help="URL del Webhook Receptor",)
    dispatcher_parser.add_argument("--secret", type=parse_secret_key, default=None, help="Clave secreta HMAC",)

    # Envío de Webhook de prueba
    test_parser = subparsers.add_parser("send-webhook", help="Enviar un Webhook HTTP de prueba",)
    test_parser.add_argument("--url", type=parse_webhook_url, default="https://webhook.site/095619c6-2d18-4850-9ac1-5c5cc3151f52/200", help="URL del Webhook Receptor",)
    test_parser.add_argument("--secret", type=parse_secret_key, default=None, help="Clave secreta HMAC",)

    return parser


def send_test_webhook(target_url: str, secret: str) -> None:
    """Envía un webhook HTTP firmado con HMAC-SHA256."""
    payload = '{"transaction_id": "tx_9981", "amount": 350.00, "status": "COMPLETED"}'
    payload_bytes = payload.encode("utf-8")
    timestamp = int(time.time())
    signature = generate_signature(secret, timestamp, payload_bytes,)
    header_val = f"t={timestamp},v1={signature}"
    headers = {"Content-Type": "application/json", "X-Webhook-Signature": header_val}

    try:
        response = requests.post(target_url, data=payload_bytes, headers=headers, timeout=5,)
        response.raise_for_status()

    except requests.exceptions.RequestException as exc:
        raise WebhookDeliveryError(f"No se pudo enviar el Webhook: {exc}") from exc

    try:
        result = response.json()
    except ValueError:
        result = response.text

    logger.info("Respuesta del receptor Webhook HTTP %s: %s", response.status_code, result)


def resolve_queue_url(queue_name: str) -> str:
    """Obtiene la URL real de una cola existente en LocalStack."""
    sqs = get_sqs_client()

    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        return response["QueueUrl"]

    except (BotoCoreError, ClientError) as exc:
        raise SQSConnectionError(
            f"No se pudo obtener la URL de la cola '{queue_name}'."
        ) from exc


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.comando in ("send-webhook", "start-dispatcher"):
        secret = args.secret or os.environ.get("WEBHOOK_SECRET")

        if not secret:
            parser.error("Configura WEBHOOK_SECRET en variables de entorno o usa --secret")

        try:
            args.secret = parse_secret_key(secret)
        except argparse.ArgumentTypeError as exc:
            parser.error(str(exc))

    logger.info("Iniciando VulcanoCLI en modo '%s'", args.comando)

    try:
        if args.comando == "send-webhook":
            send_test_webhook(args.url, args.secret)

        elif args.comando == "start-dispatcher":
            queue_url = resolve_queue_url(args.queue)
            run_dispatcher(
                queue_url=queue_url,
                wait_time=args.wait_time,
                target_url=args.url,
                secret=args.secret
            )

        elif args.comando == "produce-sqs":
            sqs = get_sqs_client()
            queue_url = resolve_queue_url(args.queue)
            event_data = {"transaction_id": "tx_9981", "amount": 350.00, "status": "COMPLETED"}

            message_id = produce_event(sqs, queue_url, event_data)

            logger.info("Evento publicado correctamente en la cola '%s'. Message_id: %s", args.queue, message_id)

        elif args.comando == "start-receiver":
            logger.info("Iniciando receptor Webhook HTTP en %s:%s...", args.host, args.port)
            uvicorn.run(app, host=args.host, port=args.port)

    except* WebhookSignatureError as group:
        logger.error("Errores de firma HMAC en Webhooks (%s):", len(group.exceptions),)
        for exc in group.exceptions:
            logger.error("  • %s", exc)

    except* WebhookTimestampError as group:
        logger.error("Errores de timestamp en Webhooks (%s):", len(group.exceptions),)
        for exc in group.exceptions:
            logger.error("  • %s", exc)

    except* SQSConnectionError as group:
        logger.error("Errores de comunicación con SQS LocalStack (%s):", len(group.exceptions),)
        for exc in group.exceptions:
            logger.error("  • %s", exc)

    except* WebhookDeliveryError as group:
        logger.error("Errores de entrega de Webhooks (%s):", len(group.exceptions),)
        for exc in group.exceptions:
            logger.error("  • %s", exc)

    except* CorruptedMessageError as group:
        logger.error(
            "Se detectaron mensajes corruptos en SQS (%s):",
            len(group.exceptions),
        )
        for exc in group.exceptions:
            logger.error("  • %s", exc)

    except* Exception as group:
        logger.error("Se produjeron errores inesperados durarte la ejecucion")
        for exc in group.exceptions:
            logger.error("  • %s", exc)

    finally:
        logger.info("Liberando recursos de observabilidad...")
        listeners = getattr(logger, "listener", None)
        if listeners is not None:
            listeners.stop()


if __name__ == "__main__":
    main()
