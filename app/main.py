from fastapi import FastAPI
import uvicorn

# Importamos la clase Calculator desde app/calculator.py.
# Como estamos dentro del paquete "app", el import usa la ruta completa desde la raíz del proyecto.
from app.calculator import Calculator

# Instancia de la aplicación FastAPI: aquí se definen las rutas y la lógica.
app = FastAPI()

# Creamos un objeto de la clase Calculator. Lo reutilizamos en las rutas.
calculator = Calculator()

# @app.get("/") es un decorator que registra la función de abajo como handler
# de peticiones GET a la ruta "/"
# Cuando alguien visita esa dirección, FastAPI ejecuta la función y devuelve su resultado como JSON.
@app.get("/")
async def inicio():
    return {"mensaje": "¡Hola desde FastAPI!"}

# Ruta de health check: sirve para comprobar que la API está viva y respondiendo.
# Herramientas como Docker, Kubernetes o balanceadores de carga suelen consultarla periódicamente.
@app.get("/health")
async def health():
    return {"estado": "ok"}

# Handler que llama al método sum() de la clase Calculator.
# Los parámetros x e y se reciben como query params, por ejemplo: /sum?x=2&y=3
# FastAPI convierte automáticamente los valores a int y valida que sean números.
@app.get("/sum")
async def suma(x: int, y: int):
    resultado = calculator.sum(x, y)
    return {"x": x, "y": y, "resultado": resultado}

# El bloque if __name__ == "__main__" solo se ejecuta cuando lanzas este archivo
# directamente (python -m app.main), no cuando otro módulo lo importa.
# Esto evita que el servidor arranque por accidente.
if __name__ == "__main__":
    # Aquí pasamos 'app' como objeto, así que no hace falta escribir "app.main:app" como cadena.
    # Esta forma no tiene --reload. Para recarga automática, usa:
    #     uvicorn.run("app.main:app", reload=True)
    # En ese caso el nombre del módulo debe ir como cadena.
    uvicorn.run(app, host="127.0.0.1", port=8000)
