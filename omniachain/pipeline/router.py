"""OmniaChain — Pipeline Router: roteamento por conteúdo/intenção."""

from __future__ import annotations

from typing import Any, Callable, Optional

from omniachain.core.context import Context


class RouterPipeline:
    """Roteia para diferentes handlers baseado em conteúdo ou intenção.

    Exemplo::

        router = RouterPipeline()
        router.route("code", handle_code)
        router.route("math", handle_math)
        router.route("general", handle_general)
        router.set_classifier(my_classifier_func)
        result = await router.run(ctx)
    """

    def __init__(self, name: str = "router") -> None:
        self.name = name
        self._routes: dict[str, Callable] = {}
        self._classifier: Optional[Callable] = None
        self._default: Optional[Callable] = None

    def route(self, intent: str, func: Callable) -> RouterPipeline:
        """Registra um handler para uma intenção."""
        self._routes[intent] = func
        return self

    def default(self, func: Callable) -> RouterPipeline:
        """Define handler padrão."""
        self._default = func
        return self

    def set_classifier(self, func: Callable) -> None:
        """Define a função classificadora de intenção."""
        self._classifier = func

    async def run(self, ctx: Optional[Context] = None) -> Context:
        """Classifica a intenção e roteia para o handler correto."""
        if ctx is None:
            ctx = Context()

        # Classificar
        if self._classifier:
            intent = await self._classifier(ctx)
        else:
            intent = self._simple_classify(ctx)

        ctx.metadata["router_intent"] = intent

        # Rotear
        handler = self._routes.get(intent, self._default)
        if handler:
            await handler(ctx)

        return ctx

    def _simple_classify(self, ctx: Context) -> str:
        """Classificação simples por keywords."""
        text = (ctx.get("query", "") or ctx.get("input", "")).lower()

        keywords = {
            "code": ["código", "code", "programa", "script", "python", "javascript"],
            "math": ["calcula", "math", "soma", "subtrai", "raiz", "equação"],
            "search": ["busca", "pesquisa", "search", "encontr"],
        }

        for intent, words in keywords.items():
            if any(w in text for w in words):
                return intent

        return "general"
