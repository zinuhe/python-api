# python-api
About APIs

API sencilla con FastAPI que expone una operación de suma.

## Instalación

```
pip install -r requirements.txt
```

## Ejecución

Desde la raíz del proyecto:

```
# Development with reload
uvicorn app.main:app --reload

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

- http://127.0.0.1:8000/ (mensaje de bienvenida)
- http://127.0.0.1:8000/health (estado de la API)
- http://127.0.0.1:8000/sum?x=2&y=3 (devuelve 5)
- http://127.0.0.1:8000/docs (documentación interactiva)
