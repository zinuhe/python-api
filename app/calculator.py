# Clase que agrupa operaciones matemáticas.
# Al estar en su propio módulo, se puede importar desde app/main.py u otros módulos.
class Calculator:
    # Método de instancia: recibe dos enteros y devuelve su suma.
    # "self" es la referencia al objeto Calculator actual (obligatorio en métodos de instancia).
    def sum(self, x: int, y: int) -> int:
        return x + y
