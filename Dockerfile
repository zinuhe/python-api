# Imagen base oficial de Python, versión slim (más ligera).
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor.
WORKDIR /code

# Copiamos primero solo requirements.txt para aprovechar la caché de Docker:
# si el código cambia pero las dependencias no, no se reinstalan.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código de la aplicación.
COPY ./app ./app

# Arranca Uvicorn escuchando en 0.0.0.0 para que sea accesible desde fuera del contenedor.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
