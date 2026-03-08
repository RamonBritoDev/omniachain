"""OmniaChain — Fallback automático entre APIs."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from omniachain.core.errors import OmniaError


class FallbackHandler:
    """Executa operações com fallback automático entre alternativas.

    Exemplo::

        handler = FallbackHandler()
        handler.add(primary_func)
        handler.add(secondary_func)
        result = await handler.execute(args)
    """

    def __init__(self, max_retries: int = 3, delay_seconds: float = 1.0) -> None:
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self._handlers: list[Callable] = []
        self._errors: list[dict[str, Any]] = []

    def add(self, func: Callable) -> FallbackHandler:
        """Adiciona um handler na cadeia de fallback."""
        self._handlers.append(func)
        return self

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Executa handlers em ordem até um funcionar."""
        import asyncio

        for i, handler in enumerate(self._handlers):
            for attempt in range(1, self.max_retries + 1):
                try:
                    return await handler(*args, **kwargs)
                except Exception as e:
                    self._errors.append({
                        "handler": handler.__name__,
                        "attempt": attempt,
                        "error": str(e),
                        "timestamp": time.time(),
                    })
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.delay_seconds * attempt)

        raise OmniaError(
            "Todos os handlers de fallback falharam.",
            suggestion="Verifique se pelo menos uma alternativa está disponível.",
            context={"errors": self._errors[-5:]},
        )

    @property
    def error_log(self) -> list[dict[str, Any]]:
        return self._errors
