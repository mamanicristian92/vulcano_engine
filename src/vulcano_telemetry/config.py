
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de AWS y LocalStack
SQS_ENDPOINT_URL = os.getenv(
    "SQS_ENDPOINT_URL",
    "http://localhost:4566"
)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

# Configuración de las colas
QUEUE_URL = os.getenv("QUEUE_URL")
WAIT_TIME_SECONDS = int(os.getenv("WAIT_TIME_SECONDS", "10"))

# Configuración de Webhooks
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DISPATCHER_TARGET_URL = os.getenv("DISPATCHER_TARGET_URL")
