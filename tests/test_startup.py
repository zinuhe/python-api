import asyncio
import logging

import httpx
from fastapi.testclient import TestClient

import app.main as main
from app.agent import ollama_problem

BASE_URL = "http://ollama.test/v1"


def check(model: str, handler) -> str | None:
    # MockTransport simula Ollama: no hace ninguna petición de red real.
    return asyncio.run(
        ollama_problem(model, BASE_URL, transport=httpx.MockTransport(handler))
    )


def models_response(*names: str):
    return lambda request: httpx.Response(200, json={"data": [{"id": n} for n in names]})


def test_no_problem_when_ollama_runs_and_has_the_model():
    assert check("ollama:qwen2.5:7b", models_response("qwen2.5:7b", "other")) is None


def test_reports_ollama_not_reachable():
    def down(request):
        raise httpx.ConnectError("refused")

    problem = check("ollama:qwen2.5:7b", down)

    assert "not reachable" in problem
    assert "ollama serve" in problem


def test_reports_model_not_installed():
    problem = check("ollama:qwen2.5:7b", models_response("llama3.2:1b"))

    assert "qwen2.5:7b" in problem
    assert "ollama pull qwen2.5:7b" in problem


def test_reports_unexpected_ollama_response_as_not_reachable():
    problem = check("ollama:qwen2.5:7b", lambda request: httpx.Response(500))

    assert "not reachable" in problem


def test_skips_the_check_for_non_ollama_models():
    def must_not_be_called(request):
        raise AssertionError("no request expected")

    assert check("anthropic:claude-sonnet-5-5", must_not_be_called) is None


# TestClient solo ejecuta el lifespan si se usa como context manager (with ...).
def test_startup_logs_model_and_ollama_warning(monkeypatch, caplog):
    async def fake_problem():
        return "Ollama is not reachable at test"

    monkeypatch.setattr(main, "ollama_problem", fake_problem)
    caplog.set_level(logging.INFO, logger="uvicorn.error")

    with TestClient(main.app):
        pass

    messages = [(r.levelno, r.getMessage()) for r in caplog.records]
    assert (logging.INFO, f"AI model: {main.MODEL}") in messages
    assert (logging.WARNING, "Ollama is not reachable at test") in messages


def test_startup_has_no_warning_when_all_is_fine(monkeypatch, caplog):
    async def fake_problem():
        return None

    monkeypatch.setattr(main, "ollama_problem", fake_problem)
    caplog.set_level(logging.INFO, logger="uvicorn.error")

    with TestClient(main.app):
        pass

    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
