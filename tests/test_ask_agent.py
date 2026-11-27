import pytest
from fastapi.testclient import TestClient
from pydantic_ai import models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from app.agent import agent, multiply_numbers, sum_numbers
from app.main import app

client = TestClient(app)

# Garantía: si algún test intentara llamar a un modelo real, falla en vez de gastar tokens.
models.ALLOW_MODEL_REQUESTS = False


# Las herramientas son funciones normales de Python, se pueden probar sin agente ni modelo.
def test_tools_call_the_calculator():
    assert sum_numbers(2, 3) == 5
    assert multiply_numbers(6, 7) == 42


# TestModel es un modelo falso de PydanticAI: no llama a ninguna API.
# custom_output_args fija la respuesta final que "devuelve el modelo".
# Con esto probamos el endpoint (ruta, validación y formato de salida) sin API key.
def test_ask_returns_typed_answer():
    fake = TestModel(
        custom_output_args={
            "operation": "multiply",
            "x": 6,
            "y": 7,
            "result": 42,
            "explanation": "6 times 7",
        }
    )

    with agent.override(model=fake):
        response = client.get("/ask", params={"question": "cuanto es 6 por 7"})

    assert response.status_code == 200
    assert response.json() == {
        "operation": "multiply",
        "x": 6,
        "y": 7,
        "result": 42,
        "explanation": "6 times 7",
    }


# FunctionModel permite escribir a mano el "guion" del modelo:
#   turno 1: el modelo pide llamar a la herramienta multiply_numbers(6, 7)
#   turno 2: ya con el resultado de la herramienta, entrega la respuesta final.
# Si el resultado del endpoint es 42, es porque la herramienta se ejecutó de verdad
# (llamó a Calculator.multiply) y el agente usó su resultado.
def test_ask_runs_the_tool_through_the_agent():
    def scripted_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool_return = next(
            (
                part
                for message in messages
                for part in message.parts
                if isinstance(part, ToolReturnPart)
            ),
            None,
        )
        if tool_return is None:
            return ModelResponse(
                parts=[ToolCallPart("multiply_numbers", {"x": 6, "y": 7})]
            )
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "operation": "multiply",
                        "x": 6,
                        "y": 7,
                        "result": tool_return.content,
                        "explanation": "used multiply_numbers",
                    },
                )
            ]
        )

    with agent.override(model=FunctionModel(scripted_model)):
        response = client.get("/ask", params={"question": "cuanto es 6 por 7"})

    assert response.status_code == 200
    assert response.json()["result"] == 42


# "question" es obligatorio: FastAPI responde 422 antes de llegar al agente.
def test_ask_requires_question():
    response = client.get("/ask")

    assert response.status_code == 422


# Si el agente decide que la pregunta no es soportada (por ejemplo una división), devuelve
# UnsupportedOperation. El endpoint lo convierte en 422 con un mensaje claro (error del cliente).
def test_ask_unsupported_operation_returns_422():
    def scripted_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        # Elegimos la herramienta de salida UnsupportedOperation entre las disponibles.
        tool = next(t for t in info.output_tools if t.name.endswith("UnsupportedOperation"))
        return ModelResponse(parts=[ToolCallPart(tool.name, {"reason": "division is not available"})])

    with agent.override(model=FunctionModel(scripted_model)):
        response = client.get("/ask", params={"question": "cuanto es 10 dividido entre 5"})

    assert response.status_code == 422
    assert "Operation not supported" in response.json()["detail"]


# Si el modelo falla (Ollama apagado, sin key, salida inválida...), es un error del servidor:
# 502 con un mensaje genérico, sin filtrar el detalle interno al cliente.
def test_ask_returns_502_when_the_model_fails():
    def broken_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise UnexpectedModelBehavior("secret internal detail")

    with agent.override(model=FunctionModel(broken_model)):
        response = client.get("/ask", params={"question": "cuanto es 6 por 7"})

    assert response.status_code == 502
    assert response.json() == {"detail": "The AI model failed or is unavailable."}
    assert "secret" not in response.text
