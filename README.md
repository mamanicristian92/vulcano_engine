# Proyecto Vulcano


### Características



### Tecnologías

- Python
- pip
- boto3

### Requisitos

- Python 3.11 o superior

## Instalación

1.  Clonar el repositorio

    1. Ve a la carpeta donde quieres guardar el proyecto:
        
        ```bash
        cd ruta/de/la/carpeta
        ```
    2. Clona el repositorio:
        
        ```bash
        git clone git@github.com:mamanicristian92/vulcano_engine.git
        ```
    3. Entra al proyecto:
        
        ```bash
        cd vulcano_engine
        ```

2. Instalar dependencias
    
    1. Crear el entorno virtual

        Dentro de la carpeta del proyecto:
        
        - Windows:

            ```bash
            python -m venv .venv
            ```
        
        - Linux / macOS:

            ```bash
            python3 -m venv .venv
            ```
        
        Esto crea una carpeta llamada `.venv`.
    
    2. Activarlo

        - Windows (PowerShell):

            ```bash
            .\.venv\Scripts\Activate.ps1
            ```

        - Linux / macOS:
            
            ```bash
            source .venv/bin/activate
            ```
        
        - Cuando esté activado, normalmente verás algo como:

            ```bash
            (.venv) $
            ```

    3. Instalar paquetes:
    
        - Con el entorno activado:

            ```bash
            pip install -r requirements.txt
            ```


3. Levantar Localstack (con Docker instalado y corriendo en el sistema)

    - Desde la carpeta del proyecto:

        ```bash
        docker compose up -d
        ```
    
    - Revisar que esté en ejecución:

        ```bash
        docker ps
        ```

        Nota: Esto crea y levanta localstack y crea la cola de eventos

4. Levantar API weebhook_receiver

    - En otra terminal, con el **entorno activado** y en la carpeta raíz:

        ```bash
        uvicorn src.vulcano_telemetry.webhook_receiver:app --reload
        ```

## Cómo Usar

Con Localstack y la API en ejecución, podemos ejecutar app_operator.py

- Enviar un mensaje a la cola de eventos:

    ```bash
    python app_operator.py
    ```

- Consumir mensajes de la cola de eventos:

    ```bash
    python app_operator.py --mode start-dispatcher
    ```

Parámetros:

|Flag       |Short|Opciones|Descripción              |Default                        |
|-----------|-----|--------|-------------------------|-------------------------------|
|--queue    | -q  |        |Nombre de la cola SQS    |vulcano-events-queue           |
|--wait-time| -w  |[1-20]  |Tiempo de Long Polling   |                               |
|--url      |     |        |URL del Webhook Receptor | http://localhost:8000/webhook |
|--secret   |     |        |Clave secreta HMAC       |                               |
|--mode     |     |send-webhook <br> start-dispatcher| Modo operativo   | send-webhook      |

**Ejemplo:**

Probar usar una clave distinta a la default:

```bash
python app_operator.py --secret mi_clave_equivocada_no_tan_secreta_456
```

Esto generará un 401 Unauthorized en el webhook_receiver

---

### Calidad y pruebas

El proyecto cuenta con pruebas automatizadas y herramientas de análisis estático
(Flake8 y Pylint) para verificar su correcto funcionamiento y mantener la
calidad del código.

Para conocer cómo ejecutar las pruebas y las herramientas de análisis,
consultar [CONTRIBUTING.md](CONTRIBUTING.md).

---

###  Diagrama de Arquitectura de Telemetría


---

### Equipo de desarrollo

### Equipo 404

- Integrante 1: [Lescano, Jessica Daiana](https://www.github.com/daylagitana89jl-oss)
- Integrante 2: [Venticola, Leandro Enrique](https://github.com/leoventicola/)
- Integrante 3: [Cointte Cedron, Mateo](https://github.com/Th-30Mateo)
- Integrante 4: [Choque, Ismael Alejandro](https://www.github.com/ismahack7)
- Integrante 5: [Martinez, Gustavo Alejandro](https://www.github.com/)
- Integrante 6: [Mamaní, Cristian Alfredo](https://www.github.com/mamanicristian92)

### Video de presentación

