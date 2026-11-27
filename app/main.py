import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
import uvicorn
from pydantic_ai.exceptions import (
    AgentRunError,
    ContentFilterError,
    ModelAPIError,
    UnexpectedModelBehavior,
    UserError,
)

# Importamos la clase Calculator desde app/calculator.py.
# Como estamos dentro del paquete "app", el import usa la ruta completa desde la raíz del proyecto.
from app.calculator import Calculator

# El agente de PydanticAI vive en app/agent.py; aquí solo lo usamos en la ruta /ask.
from app.agent import MODEL, MathAnswer, UnsupportedOperation, agent, ollama_problem

logger = logging.getLogger(__name__)

# Mensajes fijos de /ask: nunca incluyen texto del modelo ni detalles internos.
UNSUPPORTED_DETAIL = "Operation not supported. Available operations: sum, multiply."
MODEL_ERROR_DETAIL = "The AI model failed or is unavailable."

# Logger de Uvicorn: sus mensajes salen con el mismo formato (INFO:     ...) y nivel que los de
# arranque. Con logging.getLogger(__name__) los info no se verían (el nivel por defecto es WARNING).
startup_logger = logging.getLogger("uvicorn.error")


# lifespan: código que corre al arrancar (antes del yield) y al apagar (después).
# Uvicorn imprime "Waiting for application startup" antes y "Application startup complete" después,
# así que nuestros mensajes salen entre esas dos líneas.
@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_logger.info("AI model: %s", MODEL)
    problem = await ollama_problem()
    if problem:
        # Solo un aviso: la app arranca igual y el resto de endpoints funcionan.
        startup_logger.warning(problem)
    yield
    # Lo que se escriba después del yield corre al apagar. Uvicorn ya imprime "Shutting down",
    # así que aquí no añadimos mensaje; sirve para cerrar conexiones, por ejemplo.


# Instancia de la aplicación FastAPI: aquí se definen las rutas y la lógica.
app = FastAPI(lifespan=lifespan)

# Creamos un objeto de la clase Calculator. Lo reutilizamos en las rutas.
calculator = Calculator()

# @app.get("/") es un decorator que registra la función de abajo como handler
# de peticiones GET a la ruta "/"
# Cuando alguien visita esa dirección, FastAPI ejecuta la función y devuelve su resultado como JSON.
@app.get("/")
async def inicio():
    return {"message": "Hello from FastAPI!"}

# Ruta de health check: sirve para comprobar que la API está viva y respondiendo.
# Herramientas como Docker, Kubernetes o balanceadores de carga suelen consultarla periódicamente.
@app.get("/health")
async def health():
    return {"status": "ok"}

# Handler que llama al método sum() de la clase Calculator.
# Los parámetros x e y se reciben como query params, por ejemplo: /sum?x=2&y=3
# FastAPI convierte automáticamente los valores a int y valida que sean números.
@app.get("/sum")
async def suma(x: int, y: int):
    result = calculator.sum(x, y)
    return {"x": x, "y": y, "result": result}

# --- Inyección de dependencias (DI) ---
# Función "proveedora": le dice a FastAPI cómo crear la dependencia.
# Si mañana la calculadora necesita configuración, solo se cambia aquí.
def get_calculator() -> Calculator:
    return Calculator()

# Compara con /sum: allí el handler usa la variable global "calculator" (la crea main.py).
# Aquí el handler recibe la calculadora por parámetro: Depends(get_calculator) hace que
# FastAPI llame a get_calculator() en cada petición y pase el resultado como "calc".
# El handler no sabe cómo se crea la calculadora, y en tests se puede reemplazar
# con app.dependency_overrides[get_calculator].
@app.get("/multiply")
async def multiplicacion(x: int, y: int, calc: Calculator = Depends(get_calculator)):
    result = calc.multiply(x, y)
    return {"x": x, "y": y, "result": result}

# Pregunta en lenguaje natural, por ejemplo: /ask?question=cuanto es 6 por 7
# El agente decide qué herramienta (suma o multiplicación) usar y devuelve un MathAnswer.
# Anotar el retorno como MathAnswer hace que FastAPI documente y valide la respuesta.
#
# Códigos de respuesta:
#   200: operación resuelta (MathAnswer).
#   422: la pregunta pide algo no soportado (por ejemplo una división), o el modelo no logró
#        una salida válida. Error del cliente.
#   502: el modelo no está disponible (Ollama apagado, sin API key, error HTTP...). Error del servidor,
#        con un mensaje genérico: el detalle se registra en el log, no se envía al cliente.
@app.get(
    "/ask",
    responses={
        422: {"description": "Operation not supported"},
        502: {"description": "The AI model failed or is unavailable"},
    },
)
async def ask(question: str) -> MathAnswer:
    try:
        result = await agent.run(question)
    except (ModelAPIError, ContentFilterError, UserError):
        # Fallos de conexión, HTTP, filtro de contenido o configuración (por ejemplo, Ollama
        # apagado o falta la API key): es un problema del servidor, no de la pregunta.
        logger.exception("The model is unavailable while answering %r", question)
        raise HTTPException(status_code=502, detail=MODEL_ERROR_DETAIL)
    except UnexpectedModelBehavior:
        # El modelo respondió pero no logró una salida válida tras todos los reintentos. Con
        # preguntas que no son suma ni multiplicación (un saludo, "2 elevado a 3") es lo que
        # suele pasar, así que se trata como operación no soportada. Riesgo conocido: una
        # pregunta soportada que el modelo no logre resolver también saldrá como 422.
        logger.warning("The model gave no valid output for %r", question, exc_info=True)
        raise HTTPException(status_code=422, detail=UNSUPPORTED_DETAIL)
    except AgentRunError:
        logger.exception("The agent failed while answering %r", question)
        raise HTTPException(status_code=502, detail=MODEL_ERROR_DETAIL)

    if isinstance(result.output, UnsupportedOperation):
        # La razón del modelo puede venir en cualquier idioma, así que solo se registra en el log.
        logger.info("Unsupported operation for %r: %s", question, result.output.reason)
        raise HTTPException(status_code=422, detail=UNSUPPORTED_DETAIL)
    return result.output

# El bloque if __name__ == "__main__" solo se ejecuta cuando lanzas este archivo
# directamente (python -m app.main), no cuando otro módulo lo importa.
# Esto evita que el servidor arranque por accidente.
if __name__ == "__main__":
    # Aquí pasamos 'app' como objeto, así que no hace falta escribir "app.main:app" como cadena.
    # Esta forma no tiene --reload. Para recarga automática, usa:
    #     uvicorn.run("app.main:app", reload=True)
    # En ese caso el nombre del módulo debe ir como cadena.
    uvicorn.run(app, host="127.0.0.1", port=8000)
