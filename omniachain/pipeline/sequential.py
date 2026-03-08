"""OmniaChain — Pipeline sequencial: steps em ordem."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from omniachain.core.chain import Chain, Step
from omniachain.core.context import Context


class SequentialPipeline:
    """Pipeline que executa steps em sequência.

    Exemplo::

        pipe = SequentialPipeline("analysis")
        pipe.add(step1_func)
        pipe.add(step2_func)
        result = await pipe.run(Context())
    """

    def __init__(self, name: str = "sequential") -> None:
        self.name = name
        self._chain = Chain(name)

    def add(self, func: Callable, *, name: Optional[str] = None, retries: int = 1, timeout: float = 30.0) -> None:
        """Adiciona um step ao pipeline."""
        step = Step(name=name or func.__name__, func=func, retries=retries, timeout=timeout)
        self._chain.add_step(step)

    def step(self, **kwargs: Any) -> Callable:
        """Decorator para adicionar um step."""
        return self._chain.step(**kwargs)

    async def run(self, ctx: Optional[Context] = None) -> Context:
        """Executa todos os steps em sequência."""
        return await self._chain.run(ctx)

    def __len__(self) -> int:
        return len(self._chain)
