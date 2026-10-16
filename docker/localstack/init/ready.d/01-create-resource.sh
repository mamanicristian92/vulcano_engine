#!/bin/bash
# Este Script crea la Queue principal, la DLQ, y los asocia
# Se podría resumir en poco más de 3 instrucciones, pero está diseñada para ser idempotente

set -e

QUEUE_NAME="vulcano-events-queue"
DLQ_NAME="vulcano-events-dlq"
MAX_RECEIVE_COUNT=3

echo "Inicializando SQS..."

# 1. Crear la DLQ si no existe
if awslocal sqs get-queue-url --queue-name "${DLQ_NAME}" > /dev/null 2>&1; then
    echo "La DLQ '${DLQ_NAME}' ya existe."
else
    echo "Creando DLQ '${DLQ_NAME}'..."
    awslocal sqs create-queue \
        --queue-name "${DLQ_NAME}" > /dev/null
    echo "DLQ '${DLQ_NAME}' creada."
fi

# 2. Obtener el ARN de la DLQ
DLQ_URL=$(awslocal sqs get-queue-url \
    --queue-name "${DLQ_NAME}" \
    --query 'QueueUrl' \
    --output text)

DLQ_ARN=$(awslocal sqs get-queue-attributes \
    --queue-url "${DLQ_URL}" \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text)

# 3. Crear la cola principal si no existe
if awslocal sqs get-queue-url --queue-name "${QUEUE_NAME}" > /dev/null 2>&1; then
    echo "La cola '${QUEUE_NAME}' ya existe."
else
    echo "Creando cola '${QUEUE_NAME}'..."
    awslocal sqs create-queue \
        --queue-name "${QUEUE_NAME}" > /dev/null
    echo "Cola '${QUEUE_NAME}' creada."
fi

# 4. Obtener la URL de la cola principal
QUEUE_URL=$(awslocal sqs get-queue-url \
    --queue-name "${QUEUE_NAME}" \
    --query 'QueueUrl' \
    --output text)

# 5. Asociar la DLQ a la cola principal
REDRIVE_POLICY=$(printf \
    '{"deadLetterTargetArn":"%s","maxReceiveCount":"%s"}' \
    "${DLQ_ARN}" "${MAX_RECEIVE_COUNT}")

awslocal sqs set-queue-attributes \
    --queue-url "${QUEUE_URL}" \
    --attributes "{\"RedrivePolicy\":\"${REDRIVE_POLICY}\"}"

echo "DLQ '${DLQ_NAME}' asociada a '${QUEUE_NAME}'."
echo "Máximo de recepciones: ${MAX_RECEIVE_COUNT}"
echo "Inicialización SQS completada."