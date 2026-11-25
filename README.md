# python-api
About APIs

API sencilla con FastAPI que expone una operación de suma.

## Instalación

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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
- http://127.0.0.1:8000/sum?x=2&y=3 (devuelve 5)
- http://127.0.0.1:8000/docs (documentación interactiva)

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
