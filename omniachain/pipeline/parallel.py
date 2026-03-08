"""OmniaChain — Pipeline paralelo com asyncio.gather."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Optional

from omniachain.core.context import Context


class ParallelPipeline:
    """Pipeline que executa steps em paralelo com asyncio.gather.

    Exemplo::

        pipe = ParallelPipeline("scraping")
        pipe.add(fetch_url1)
        pipe.add(fetch_url2)
        pipe.add(fetch_url3)
        result = await pipe.run(Context())
    """

    def __init__(self, name: str = "parallel", max_concurrent: int = 10) -> None:
        self.name = name
        self.max_concurrent = max_concurrent
        self._steps: list[tuple[str, Callable]] = []

    def add(self, func: Callable, *, name: Optional[str] = None) -> None:
        """Adiciona um step para execução paralela."""
        self._steps.append((name or func.__name__, func))

    async def run(self, ctx: Optional[Context] = None) -> Context:
        """Executa todos os steps em paralelo."""
        if ctx is None:
            ctx = Context()

        semaphore = asyncio.Semaphore(self.max_concurrent)
        results: dict[str, Any] = {}

        async def _run_step(step_name: str, func: Callable) -> None:
            async with semaphore:
                forked_ctx = ctx.fork()
                await func(forked_ctx)
                results[step_name] = forked_ctx.variables

        start = time.perf_counter()

        tasks = [_run_step(name, func) for name, func in self._steps]
        await asyncio.gather(*tasks, return_exceptions=True)

        latency = (time.perf_counter() - start) * 1000

        # Merge results back
        for step_name, step_vars in results.items():
            for key, value in step_vars.items():
                ctx.set(f"{step_name}.{key}", value)

        ctx.metadata["parallel_results"] = {
            "pipeline_name": self.name,
            "steps": len(self._steps),
            "latency_ms": latency,
        }

        return ctx

    def __len__(self) -> int:
        return len(self._steps)
