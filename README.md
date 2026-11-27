# python-api
About APIs

API sencilla con FastAPI que expone suma y multiplicación, y un endpoint `/ask` con un agente de PydanticAI.

## Instalación

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Para correr los tests (agrega pytest y httpx)
pip install -r requirements-dev.txt
```

## Ejecución

Desde la raíz del proyecto:

```
# Development with reload
uvicorn app.main:app --reload

# Development with reload (usando el uvicorn del venv directamente, sin activarlo)
.venv/bin/uvicorn app.main:app --reload

# Development
python -m app.main

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Gunicorn como gestor de procesos, con workers de Uvicorn
Es la opción clásica para producción en servidores propios. Gunicorn se encarga de gestionar los procesos (reinicia los que fallan, reparte carga) y Uvicorn atiende las peticiones async.
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 4 --bind 0.0.0.0:8000

# Docker
# docker build crea la imagen siguiendo el Dockerfile, y docker run arranca un contenedor a partir de ella.
# El -p 8000:8000 conecta el puerto 8000 de tu máquina con el del contenedor, se sigue abriendo en http://127.0.0.1:8000/
docker build -t mi-proyecto .
docker run -p 8000:8000 mi-proyecto
```

Luego prueba en el navegador:

- http://127.0.0.1:8000/ (welcome message)
- http://127.0.0.1:8000/health (API status)
- http://127.0.0.1:8000/sum?x=2&y=3 (devuelve 5; usa la calculadora global, sin DI)
- http://127.0.0.1:8000/multiply?x=4&y=5 (devuelve 20; recibe la calculadora por inyección de dependencias)
- http://127.0.0.1:8000/ask?question=cuanto es 6 por 7 (agente de PydanticAI; por defecto usa Ollama local, ver abajo)
- http://127.0.0.1:8000/docs (documentación interactiva)

## Agente con PydanticAI (`/ask`)

El código está en `app/agent.py`. Un agente recibe una pregunta en lenguaje natural, decide si usar la suma o la multiplicación, llama a `Calculator` como herramienta y devuelve una respuesta tipada (`MathAnswer`: `operation`, `x`, `y`, `result`, `explanation`).

- **API key (solo si usas Anthropic):** con Anthropic cada petición consume tokens. Define la key en tu terminal antes de levantar la app, sin escribirla en archivos del repo:

  ```
  export ANTHROPIC_API_KEY=...
  ```

- **Cambiar de modelo:** el modelo se lee de la variable de entorno `MODEL` (formato `proveedor:modelo`). Si no la defines, usa `ollama:qwen2.5:7b` (Ollama local, `OLLAMA_BASE_URL` por defecto `http://localhost:11434/v1`). Para usar Anthropic: `export ANTHROPIC_API_KEY=...` y `export MODEL=anthropic:claude-sonnet-5-5`.
- **Modelo local gratis con Ollama (para pruebas):**

  ```
  brew install ollama
  ollama serve                  # déjalo corriendo en otra terminal
  ollama pull qwen2.5:7b        # ~4,7 GB

  export MODEL=ollama:qwen2.5:7b
  export OLLAMA_BASE_URL=http://localhost:11434/v1
  .venv/bin/uvicorn app.main:app --reload
  ```

  Probados con `/ask`: `qwen2.5:7b` (recomendado, ~2-5 s por pregunta) y `qwen3:8b` (también acierta, pero es mucho más lento porque "piensa" antes de responder). Los modelos de `llama` (`llama3.2:1b`, `llama3.1:8b`) fallaron: no devuelven el formato de `MathAnswer` de forma fiable.
- **Sin Ollama corriendo (o sin key si usas Anthropic):** la app arranca normal y el resto de endpoints funcionan. Solo `/ask` responde 502 (el agente comprueba el modelo al hacer la petición, no al importar).
- **Códigos de respuesta de `/ask`:**
  - `200`: operación resuelta (`MathAnswer`).
  - `422`: la pregunta pide algo no soportado (resta, división, un saludo...), o el modelo respondió pero no logró una salida válida tras los reintentos. Ejemplo: `{"detail": "Operation not supported. Available operations: sum, multiply."}`. Es un error del cliente, no del servidor. Limitación conocida: una pregunta soportada que el modelo no logre resolver también sale como 422.
  - `502`: el modelo no está disponible (Ollama apagado, sin API key, error HTTP). Mensaje genérico `"The AI model failed or is unavailable."`; el detalle se registra en el log y no se envía al cliente.
- **Probar:**

  ```
  curl -s "http://127.0.0.1:8000/ask?question=cuanto%20es%206%20por%207" | jq
  ```

## Tests

```
.venv/bin/python -m pytest -v
```

- `tests/test_multiply_di.py`: prueba `/multiply` y reemplaza la calculadora con `app.dependency_overrides`.
- `tests/test_ask_agent.py`: prueba `/ask` **sin API key y sin llamar al modelo real**, usando `TestModel` y `FunctionModel` de PydanticAI (modelos falsos). `models.ALLOW_MODEL_REQUESTS = False` hace que el test falle si algo intentara llamar a un modelo real.

## Probar los endpoints desde la terminal

Con la API corriendo en `127.0.0.1:8000`. Las comillas en las URLs con `&` son necesarias, porque si no zsh interpreta el `&` como "ejecutar en segundo plano".

### curl + jq

`curl` viene instalado en macOS. `jq` da formato (indentación y colores) al JSON.

```
# Instalar jq
brew install jq

# Probar (-s quita la barra de progreso de curl)
curl -s http://127.0.0.1:8000/ | jq
curl -s http://127.0.0.1:8000/health | jq
curl -s "http://127.0.0.1:8000/sum?x=2&y=3" | jq
```

### curl + python -m json.tool

No necesita instalar nada, solo Python. El formato es el mismo, pero sin colores.

```
curl -s http://127.0.0.1:8000/ | python3 -m json.tool
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s "http://127.0.0.1:8000/sum?x=2&y=3" | python3 -m json.tool
```

Para ver el código de estado y las cabeceras (por ejemplo, el 422 cuando x no es un número), usa `curl -i` sin el pipe:

```
curl -i "http://127.0.0.1:8000/sum?x=abc&y=3"
```

---
## Workers en Uvicorn

Un worker es un proceso independiente que ejecuta una copia de tu aplicación y atiende peticiones. Si configuras --workers 4, Uvicorn lanza cuatro procesos, cada uno con su propia copia de app, y reparte las peticiones entre ellos.

¿Por qué sirve? Python ejecuta un solo hilo de código a la vez por proceso (por el GIL), así que con un único proceso solo usas un núcleo de la CPU. Con varios workers puedes aprovechar varios núcleos. Además, si un proceso se bloquea o falla, los demás siguen atendiendo.

Ojo con dos cosas:
- Cada worker tiene su propia memoria. Si guardas datos en una variable global (un contador, una caché en memoria), cada proceso tendrá su copia y los valores no se comparten. Para eso se usan bases de datos o Redis.
- Con async, un solo worker ya atiende muchas peticiones concurrentes mientras espera I/O (base de datos, llamadas a un LLM). Los workers multiplican la capacidad sobre todo para tareas con mucho cálculo en CPU.


## Gunicorn

Gunicorn es un servidor WSGI/ASGI de Python que funciona como gestor de procesos. No atiende las peticiones HTTP por sí mismo en este caso; lo que hace es:

Lanzar y mantener vivo un número fijo de workers.
Reiniciar automáticamente los que fallan.
Gestionar reinicios sin tiempo de caída (graceful reload).

Por eso se combina con los workers de Uvicorn: Gunicorn gestiona los procesos y cada uno de esos procesos es un UvicornWorker que sí habla HTTP y ejecuta la app async.

## ¿Cuál usar?
Uvicorn solo con --workers: suficiente para muchos casos, sobre todo si la plataforma (Docker, Kubernetes, Cloud Run) ya reinicia contenedores que fallan y escala réplicas por ti.
Gunicorn + UvicornWorker: útil en servidores propios o VMs donde quieres un gestor de procesos robusto por encima de Uvicorn.

En contenedores, lo habitual hoy es una instancia de Uvicorn por contenedor y escalar con más contenedores, en lugar de muchos workers dentro de uno.
