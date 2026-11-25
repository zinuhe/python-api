from fastapi.testclient import TestClient

from app.main import app, get_calculator

client = TestClient(app)


# Test normal: usa la calculadora real que entrega get_calculator().
def test_multiply_with_real_calculator():
    response = client.get("/multiply", params={"x": 4, "y": 5})

    assert response.status_code == 200
    assert response.json() == {"x": 4, "y": 5, "result": 20}


# Test con DI: reemplazamos la dependencia por una calculadora falsa.
# El resultado 999 no puede venir de una multiplicación real, así que si aparece,
# demuestra que el handler usó la dependencia inyectada y no una creada por él mismo.
def test_multiply_with_fake_calculator():
    class FakeCalculator:
        def multiply(self, x: int, y: int) -> int:
            return 999

    app.dependency_overrides[get_calculator] = lambda: FakeCalculator()
    try:
        response = client.get("/multiply", params={"x": 4, "y": 5})
    finally:
        # Siempre limpiamos el override para no afectar a otros tests.
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"x": 4, "y": 5, "result": 999}


# FastAPI valida los tipos antes de llegar al handler: x no es un entero.
def test_multiply_rejects_non_integer():
    response = client.get("/multiply", params={"x": "abc", "y": 5})

    assert response.status_code == 422
