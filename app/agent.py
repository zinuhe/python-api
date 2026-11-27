from pydantic import BaseModel
from pydantic_ai import Agent

from app.calculator import Calculator

calculator = Calculator()


# Salida tipada: el agente está obligado a devolver exactamente este formato.
# PydanticAI valida la respuesta del modelo contra esta clase y, si no cumple, le pide que corrija.
class MathAnswer(BaseModel):
    operation: str  # "sum" o "multiply"
    x: int
    y: int
    result: int
    explanation: str


# El agente. "anthropic:claude-sonnet-5-5" es proveedor:modelo y necesita la variable de entorno
# ANTHROPIC_API_KEY, pero solo cuando se hace una petición real al modelo.
# defer_model_check=True evita que se exija la key al importar el módulo (así la app y los tests
# arrancan sin key); la comprobación se hace en agent.run().
agent = Agent(
    "anthropic:claude-sonnet-5-5",
    output_type=MathAnswer,
    instructions=(
        "Resuelve la pregunta usando las herramientas disponibles. "
        "Nunca calcules el resultado tú mismo."
    ),
    defer_model_check=True,
)


# @agent.tool_plain registra una función como herramienta que el modelo puede decidir llamar.
# "plain" significa que la herramienta no necesita contexto (RunContext). PydanticAI usa los
# type hints y el docstring para describirle la herramienta al modelo.
@agent.tool_plain
def sum_numbers(x: int, y: int) -> int:
    """Suma dos números enteros."""
    return calculator.sum(x, y)


@agent.tool_plain
def multiply_numbers(x: int, y: int) -> int:
    """Multiplica dos números enteros."""
    return calculator.multiply(x, y)
