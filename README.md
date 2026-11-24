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
uvicorn app.main:app --reload
```

Luego prueba en el navegador:

- http://127.0.0.1:8000/ (mensaje de bienvenida)
- http://127.0.0.1:8000/health (estado de la API)
- http://127.0.0.1:8000/sum?x=2&y=3 (devuelve 5)
- http://127.0.0.1:8000/docs (documentación interactiva)
