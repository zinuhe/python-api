import os
from typing import Literal

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


# Modelo a usar, en formato proveedor:modelo. Se lee de la variable de entorno MODEL para poder
# cambiarlo sin tocar el código. Por defecto, Anthropic (necesita ANTHROPIC_API_KEY).
# Para un modelo local con Ollama: MODEL=ollama:llama3.2:1b y OLLAMA_BASE_URL=http://localhost:11434/v1
MODEL = os.getenv("MODEL", "anthropic:claude-sonnet-5-5")

# El agente. defer_model_check=True evita que se exija la key o la URL al importar el módulo
# (así la app y los tests arrancan sin ellas); la comprobación se hace en agent.run().
agent = Agent(
    MODEL,
    output_type=MathAnswer,
    instructions=(
        "Resuelve la pregunta usando las herramientas disponibles. "
        "Nunca calcules el resultado tú mismo."
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
    """Suma dos números enteros."""
    return calculator.sum(x, y)


@agent.tool_plain
def multiply_numbers(x: int, y: int) -> int:
    """Multiplica dos números enteros."""
    return calculator.multiply(x, y)
