"""OmniaChain — Router inteligente por tarefa."""

from __future__ import annotations

from typing import Any, Optional

from omniachain.providers.base import BaseProvider


class TaskRouter:
    """Roteia tarefas para o provider/agente mais apropriado.

    Exemplo::

        router = TaskRouter()
        router.add_route("vision", vision_provider, keywords=["imagem", "foto", "screenshot"])
        router.add_route("code", code_provider, keywords=["código", "python", "debug"])
        provider = router.route("Analise esta imagem")
    """

    def __init__(self) -> None:
        self._routes: list[dict[str, Any]] = []
        self._default: Optional[Any] = None

    def add_route(self, name: str, handler: Any, *, keywords: list[str] | None = None, condition: Any = None) -> None:
        """Registra uma rota."""
        self._routes.append({
            "name": name,
            "handler": handler,
            "keywords": [k.lower() for k in (keywords or [])],
            "condition": condition,
        })

    def set_default(self, handler: Any) -> None:
        """Define handler padrão."""
        self._default = handler

    def route(self, task: str) -> Any:
        """Roteia uma tarefa para o handler mais apropriado."""
        task_lower = task.lower()

        # Verificar condições customizadas
        for r in self._routes:
            if r["condition"] and r["condition"](task):
                return r["handler"]

        # Verificar keywords
        best_match = None
        best_score = 0
        for r in self._routes:
            score = sum(1 for kw in r["keywords"] if kw in task_lower)
            if score > best_score:
                best_score = score
                best_match = r["handler"]

        return best_match or self._default
