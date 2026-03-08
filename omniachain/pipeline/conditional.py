"""OmniaChain — Pipeline condicional: branching por condição."""

from __future__ import annotations

from typing import Any, Callable, Optional

from omniachain.core.context import Context


class ConditionalPipeline:
    """Pipeline com branching condicional.

    Exemplo::

        pipe = ConditionalPipeline("routing")
        pipe.when(lambda ctx: ctx.get("type") == "image", process_image)
        pipe.when(lambda ctx: ctx.get("type") == "text", process_text)
        pipe.otherwise(fallback_handler)
        result = await pipe.run(ctx)
    """

    def __init__(self, name: str = "conditional") -> None:
        self.name = name
        self._branches: list[tuple[Callable[[Context], bool], Callable]] = []
        self._otherwise: Optional[Callable] = None

    def when(self, condition: Callable[[Context], bool], func: Callable) -> ConditionalPipeline:
        """Adiciona um branch condicional."""
        self._branches.append((condition, func))
        return self

    def otherwise(self, func: Callable) -> ConditionalPipeline:
        """Define o handler fallback."""
        self._otherwise = func
        return self

    async def run(self, ctx: Optional[Context] = None) -> Context:
        """Executa o primeiro branch cuja condição é verdadeira."""
        if ctx is None:
            ctx = Context()

        for condition, func in self._branches:
            if condition(ctx):
                await func(ctx)
                ctx.metadata["conditional_branch"] = func.__name__
                return ctx

        if self._otherwise:
            await self._otherwise(ctx)
            ctx.metadata["conditional_branch"] = "otherwise"

        return ctx
