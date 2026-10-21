"""Cliente Boto3 y operaciones de mensajería SQS con soporte para LocalStack."""

import json
import logging
import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from .exceptions import SQSConnectionError, CorruptedMessageError

load_dotenv()

logger = logging.getLogger("vulcano_engine")

def get_sqs_client(endpoint_url: str = "http://localhost:4566"):
    """Crea una instancia del cliente Boto3 SQS configurada para LocalStack."""
    return boto3.client(
        "sqs",
        endpoint_url=os.getenv("SQS_ENDPOINT_URL", endpoint_url),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test")
    )

def produce_event(sqs_client, queue_url: str, event_data: dict) -> str:
    """Publica un evento estructurado en la cola de SQS usando Boto3."""
    try:
        payload = json.dumps(event_data)
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=payload,
            MessageAttributes={
                "Source": {"DataType": "String", "StringValue": "VulcanoWebhookEngine"}
            }
        )
        msg_id = response.get("MessageId", "N/A")
        logger.info(f"Evento publicado en SQS. MessageId: {msg_id}", extra={"message_id": msg_id})
        return msg_id
    except ClientError as err:
        sqs_err = SQSConnectionError("Error al enviar mensaje a AWS SQS LocalStack.")
        sqs_err.add_note(f"QueueUrl: {queue_url}")
        raise sqs_err from err

def consume_events(sqs_client, queue_url: str, wait_time: int = 10, max_messages: int = 5):
    """Consume mensajes de SQS aplicando Long Polling y borrado explícito."""
    try:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            MessageAttributeNames=["All"]
        )
        messages = response.get("Messages", [])
        processed = []
        for msg in messages:
            try:
                body = json.loads(msg["Body"])
                processed.append({"receipt_handle": msg["ReceiptHandle"], "message_id": msg["MessageId"], "body": body})
            except json.JSONDecodeError as err:
                corrupt_err = CorruptedMessageError(f"Mensaje SQS corrupto ID {msg['MessageId']}")
                raise corrupt_err from err
        return processed
    except ClientError as err:
        sqs_err = SQSConnectionError("Error en recepción de mensajes SQS.")
        raise sqs_err from err
