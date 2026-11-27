import os
from typing import Literal

import httpx
from pydantic import BaseModel
from pydantic_ai import Agent

from app.calculator import Calculator

calculator = Calculator()


# Salida tipada: el agente está obligado a devolver exactamente este formato.
# PydanticAI valida la respuesta del modelo contra esta clase y, si no cumple, le pide que corrija.
class MathAnswer(BaseModel):
    # Literal limita los valores permitidos: así cada modelo debe usar exactamente uno de estos dos
    # nombres, en vez de inventar variantes ("multiplication", "multiplicación", etc.).
    operation: Literal["sum", "multiply"]
    x: int
    y: int
    result: int
    explanation: str


# Segunda salida posible: el agente la devuelve cuando la pregunta pide algo que no puede hacer
# (por ejemplo una división). Sin esta opción, el modelo no tendría una salida válida para ese caso
# y la petición terminaría en error 500. El endpoint la convierte en un 422 con un mensaje claro.
class UnsupportedOperation(BaseModel):
    reason: str


# Modelo a usar, en formato proveedor:modelo. Se lee de la variable de entorno MODEL para poder
# cambiarlo sin tocar el código. Por defecto, un modelo local con Ollama (gratis, sin key):
# requiere tener Ollama corriendo y el modelo bajado (ollama pull qwen2.5:7b).
# Para usar Anthropic: exporta ANTHROPIC_API_KEY y MODEL=anthropic:claude-sonnet-5-5
# (o descomenta la línea de abajo y comenta la de Ollama).
# MODEL = os.getenv("MODEL", "anthropic:claude-sonnet-5-5")
MODEL = os.getenv("MODEL", "ollama:qwen2.5:7b")

# PydanticAI exige OLLAMA_BASE_URL para usar el proveedor de Ollama. Si no la definiste,
# usamos la dirección local por defecto de Ollama.
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434/v1")

OLLAMA_BASE_URL = os.environ["OLLAMA_BASE_URL"]


# Comprueba al arrancar si Ollama responde y si el modelo está descargado. Devuelve un texto con el
# problema, o None si todo está bien (o si el modelo no es de Ollama). Nunca lanza excepciones:
# es solo un aviso, la app arranca igual. "transport" permite simular Ollama en los tests.
async def ollama_problem(
    model: str = MODEL,
    base_url: str = OLLAMA_BASE_URL,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str | None:
    if not model.startswith("ollama:"):
        return None
    name = model.removeprefix("ollama:")
    base_url = base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=2, transport=transport) as client:
            response = await client.get(f"{base_url}/models")
            response.raise_for_status()
            installed = {item["id"] for item in response.json()["data"]}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return (
            f"Ollama is not reachable at {base_url}. Start it with 'ollama serve'; "
            "/ask will return 502 until then."
        )
    if name not in installed:
        return f"Model '{name}' is not installed in Ollama. Run: ollama pull {name}"
    return None


# El agente. defer_model_check=True evita que se exija la key o la URL al importar el módulo
# (así la app y los tests arrancan sin ellas); la comprobación se hace en agent.run().
agent = Agent(
    MODEL,
    # Una lista de tipos significa "puede devolver cualquiera de estos".
    output_type=[MathAnswer, UnsupportedOperation],
    instructions=(
        "Answer the question using the available tools. "
        "Never compute the result yourself. "
        "The only supported operations are the sum and the multiplication of two integers. "
        "If the question asks for any other operation (subtraction, division, etc.) or is not "
        "a math question, return UnsupportedOperation with the reason; do not try to solve it."
    ),
    defer_model_check=True,
    # Reintentos si el modelo devuelve una salida inválida o llama mal a una herramienta.
    # El valor por defecto (1) se queda corto con modelos locales pequeños.
    retries=4,
)


# @agent.tool_plain registra una función como herramienta que el modelo puede decidir llamar.
# "plain" significa que la herramienta no necesita contexto (RunContext). 
# PydanticAI usa los type hints y el docstring para describirle la herramienta al modelo.
@agent.tool_plain
def sum_numbers(x: int, y: int) -> int:
    """Add two integers."""
    return calculator.sum(x, y)


@agent.tool_plain
def multiply_numbers(x: int, y: int) -> int:
    """Multiply two integers."""
    return calculator.multiply(x, y)
