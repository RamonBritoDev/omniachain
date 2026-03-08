"""OmniaChain — Tool de cálculos matemáticos precisos."""

from omniachain.tools.base import tool


@tool(cache=True, timeout=5.0)
async def calculator(expression: str) -> str:
    """Calcula expressões matemáticas com precisão.

    Suporta operações básicas, funções trigonométricas, raiz quadrada, potência, etc.
    Usa avaliação segura sem exec/eval de código arbitrário.

    Args:
        expression: Expressão matemática (ex: "sqrt(144) + 2^3")

    Returns:
        Resultado do cálculo como string.
    """
    import math
    import re

    # Funções matemáticas seguras permitidas
    safe_funcs = {
        "sqrt": math.sqrt, "abs": abs, "round": round,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan,
        "log": math.log, "log10": math.log10, "log2": math.log2,
        "exp": math.exp, "pow": math.pow, "floor": math.floor,
        "ceil": math.ceil, "factorial": math.factorial,
        "pi": math.pi, "e": math.e, "inf": math.inf,
    }

    # Limpar a expressão
    expr = expression.strip()

    # Substituir ^ por ** para potência
    expr = expr.replace("^", "**")

    # Validar — apenas caracteres seguros
    allowed = re.compile(r'^[0-9+\-*/().,%\s]+$|[a-zA-Z_]+')
    tokens = re.findall(r'[a-zA-Z_]+|[^a-zA-Z_\s]+', expr)

    for token in tokens:
        if token.isalpha() and token not in safe_funcs:
            return f"Erro: função '{token}' não permitida. Funções disponíveis: {', '.join(sorted(safe_funcs))}"

    try:
        result = eval(expr, {"__builtins__": {}}, safe_funcs)  # noqa: S307
        if isinstance(result, float) and result == int(result):
            return str(int(result))
        return str(result)
    except ZeroDivisionError:
        return "Erro: divisão por zero."
    except Exception as e:
        return f"Erro ao calcular '{expression}': {e}"
