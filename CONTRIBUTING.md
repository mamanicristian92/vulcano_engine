# Contribuir: Pruebas de Caos y Pruebas Forenses

## 1. Alcance

Este documento describe cómo ejecutar y contribuir a las pruebas correspondientes al Integrante 6 del proyecto Vulcano Engine.

Las pruebas se encuentran principalmente en:

- `tests/test_chaos.py`: pruebas de simulación de fallos y comportamiento ante mensajes inválidos.
- `tests/test_forensic_log.py`: pruebas de integridad, compresión y contenido de los registros forenses.

El objetivo es verificar que el sistema rechace solicitudes inválidas, gestione correctamente los mensajes venenosos mediante SQS y genere registros forenses íntegros.

## 2. Requisitos

Antes de ejecutar las pruebas, se necesita:

- Python y el entorno virtual del proyecto.
- Las dependencias instaladas desde `requirements.txt`.
- Docker y LocalStack en ejecución.
- Las colas SQS del proyecto creadas y configuradas.
- Las variables de entorno necesarias para la conexión con LocalStack y la autenticación de webhooks.

**Importante:** durante la ejecución de las pruebas no deben estar levantados el servidor HTTP (Uvicorn/FastAPI) ni el dispatcher.

Las pruebas HTTP utilizan el cliente de pruebas de FastAPI (`TestClient`), por lo que no necesitan un servidor HTTP en ejecución.

Las operaciones sobre SQS se realizan directamente desde los tests mediante Boto3, permitiendo controlar la recepción, eliminación y reintentos de los mensajes sin interferencia de otros consumidores.

## Consideraciones sobre el dispatcher

El dispatcher (`run_dispatcher()`) debe permanecer detenido durante la ejecución general de las pruebas, especialmente durante aquellas que verifican los reintentos y la derivación de mensajes venenosos a la Dead Letter Queue (DLQ).

**Excepción: `test_mensaje_valido_se_consum_y_elimina()`**

Esta prueba constituye una prueba de integración del flujo de despacho. Requiere que `run_dispatcher()` esté en ejecución para comprobar que:

1. Un mensaje válido llega a SQS.
2. El dispatcher recibe el mensaje.
3. `dispatch_webhook()` lo entrega correctamente al destino HTTP.
4. El dispatcher elimina el mensaje de la cola principal.
5. La cola vuelve a su tamaño inicial.

El destino HTTP debe estar disponible y responder exitosamente para que el dispatcher complete la eliminación del mensaje.

Esta prueba debe ejecutarse de forma aislada respecto de las pruebas de mensajes venenosos, evitando que otros consumidores interfieran con los mensajes de SQS.

## 3. Preparación del entorno

Activar el entorno virtual:

```bash
source .venv/bin/activate
```

Instalar las dependencias, si todavía no están instaladas:

```bash
pip install -r requirements.txt
```

Verificar que LocalStack esté activo y que las colas requeridas existan:

- `vulcano-events-queue`
- `vulcano-events-dlq`

## 4. Ejecución de las pruebas

Ejecutar todas las pruebas asignadas:

```bash
PYTHONPATH=src python -m pytest -v tests/test_chaos.py tests/test_forensic_log.py
```

- Ejecutar únicamente las pruebas de caos:

    ```bash
    PYTHONPATH=src python -m pytest -v tests/test_chaos.py
    ```

- Ejecutar únicamente las pruebas forenses:

    ```bash
    PYTHONPATH=src python -m pytest -v tests/test_forensic_log.py
    ```

Para obtener información adicional durante la ejecución:

```bash
PYTHONPATH=src python -m pytest -v -s tests/test_chaos.py
```

## 5. Pruebas de caos

Las pruebas de caos verifican los siguientes escenarios:

- **Firma incorrecta:** una firma HMAC alterada o una clave secreta incorrecta debe provocar el rechazo de la solicitud.
- **Payload alterado:** modificar el contenido de una solicitud sin actualizar su firma debe provocar un rechazo.
- **Timestamp vencido:** una marca temporal fuera del período de tolerancia debe ser rechazada mediante el mecanismo de validación correspondiente.
- **Mensaje venenoso:** un mensaje con contenido inválido debe provocar un error de procesamiento y permanecer sin eliminar hasta agotar los reintentos.
- **Dead Letter Queue:** después de alcanzar el límite de recepción configurado, SQS debe derivar automáticamente el mensaje a la DLQ.

Las pruebas que utilizan SQS deben evitar interferir con mensajes ajenos al escenario de prueba.

## 6. Pruebas forenses

Las pruebas forenses inspeccionan los archivos de registro comprimidos (`.log.gz`) y verifican:

- Que los archivos puedan descomprimirse y leerse correctamente.
- Que la información registrada se conserve después de la compresión.
- Que estén presentes los campos de trazabilidad requeridos:
  - `TraceId`
  - `MessageId`
  - `X-Webhook-Signature`

Los registros deben corresponder a eventos generados durante la ejecución de las pruebas.

## 7. Interpretación de resultados

Pytest puede informar los siguientes estados:

- **PASSED:** la prueba se ejecutó y cumplió las condiciones esperadas.
- **FAILED:** la prueba se ejecutó, pero una o más condiciones no se cumplieron.
- **SKIPPED:** la prueba fue omitida intencionalmente por una condición o dependencia no satisfecha.
- **XFAIL:** la prueba falló como se esperaba porque está marcada como una falla conocida.
- **XPASS:** una prueba marcada como falla esperada pasó inesperadamente.

Una prueba omitida no demuestra que el comportamiento del sistema sea correcto. Si una prueba se omite por problemas de configuración o por interferencia de mensajes en las colas, debe revisarse la causa.

## 8. Consideraciones para contribuir

- Mantener los tests enfocados en los requisitos establecidos por el TP.
- No modificar código de producción como parte de una corrección de tests sin coordinarlo con el responsable del componente.
- Utilizar identificadores únicos para los mensajes generados por las pruebas.
- Evitar eliminar o purgar mensajes que no pertenezcan al escenario de prueba.
- Restaurar las configuraciones temporales de SQS después de cada ejecución.
- Informar los defectos detectados en los componentes de otros integrantes, indicando la prueba afectada y el resultado observado.

## 9. Reporte de errores

Cuando una prueba falle:

1. Registrar el nombre de la prueba afectada.
2. Conservar el mensaje de error y el resultado obtenido.
3. Identificar si el problema corresponde al test, a la configuración del entorno o al comportamiento del componente probado.
4. Informar al responsable del componente cuando se detecte un defecto de implementación.

