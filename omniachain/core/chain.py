"""
OmniaChain — Chain: unidade atômica de execução.

Um Chain é uma sequência de Steps que transforma um input em output.
Cada Step é uma função async que recebe e retorna um Context.

Exemplo de uso::

    chain = Chain("meu-chain")

    @chain.step
    async def preparar(ctx: Context) -> Context:
        ctx.set("query_clean", ctx.get("query").strip().lower())
        return ctx

    @chain.step
    async def processar(ctx: Context) -> Context:
        result = await llm.complete(ctx.get("query_clean"))
        ctx.set("result", result)
        return ctx

    result = await chain.run(Context(variables={"query": "Olá!"}))
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Callable, Coroutine, Optional

from pydantic import BaseModel, Field

from omniachain.core.context import Context
from omniachain.core.errors import OmniaError, PipelineError


# Type alias para um step function
StepFunc = Callable[[Context], Coroutine[Any, Any, Context]]


class StepResult(BaseModel):
    """Resultado de execução de um step individual."""

    step_name: str
    success: bool = True
    latency_ms: float = 0.0
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Step(BaseModel):
    """Representação de um step em um chain.

    Attributes:
        name: Nome descritivo do step.
        func: Função async que processa o contexto.
        retries: Número de tentativas em caso de falha.
        timeout: Timeout máximo em segundos.
        condition: Função que determina se o step deve executar.
    """

    name: str
    func: Optional[StepFunc] = None
    retries: int = 1
    timeout: float = 30.0
    condition: Optional[Callable[[Context], bool]] = None

    async def execute(self, ctx: Context) -> StepResult:
        """Executa o step com retry e timeout.

        Args:
            ctx: Contexto atual.

        Returns:
            StepResult com métricas de execução.

        Raises:
            PipelineError: Se todas as tentativas falharem.
        """
        if self.condition and not self.condition(ctx):
            return StepResult(
                step_name=self.name,
                success=True,
                metadata={"skipped": True, "reason": "condition not met"},
            )

        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            start = time.perf_counter()
            try:
                if self.func is None:
                    raise PipelineError(
                        f"Step '{self.name}' não tem função definida.",
                        step=self.name,
                        suggestion="Defina uma função usando @chain.step ou Step(func=...).",
                    )
                await asyncio.wait_for(self.func(ctx), timeout=self.timeout)
                latency = (time.perf_counter() - start) * 1000
                return StepResult(
                    step_name=self.name,
                    success=True,
                    latency_ms=latency,
                    metadata={"attempt": attempt},
                )
            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError(
                    f"Step '{self.name}' excedeu timeout de {self.timeout}s"
                )
            except OmniaError:
                raise
            except Exception as e:
                last_error = e

        latency = (time.perf_counter() - start) * 1000
        raise PipelineError(
            f"Step '{self.name}' falhou após {self.retries} tentativa(s).",
            step=self.name,
            suggestion=f"Verifique a função do step. Último erro: {last_error}",
            original_error=last_error if isinstance(last_error, Exception) else None,
        )

    model_config = {"arbitrary_types_allowed": True}


class Chain:
    """Unidade atômica de execução: uma sequência nomeada de Steps.

    Exemplo::

        chain = Chain("analysis")

        @chain.step
        async def step1(ctx: Context) -> Context:
            ctx.set("data", "processed")
            return ctx

        result_ctx = await chain.run(Context())
        print(result_ctx.get("data"))  # "processed"
    """

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.steps: list[Step] = []
        self.chain_id: str = uuid.uuid4().hex[:12]

    def step(
        self,
        func: Optional[StepFunc] = None,
        *,
        name: Optional[str] = None,
        retries: int = 1,
        timeout: float = 30.0,
        condition: Optional[Callable[[Context], bool]] = None,
    ) -> Any:
        """Decorator para registrar um step no chain.

        Args:
            func: Função async a executar.
            name: Nome do step (default: nome da função).
            retries: Tentativas em caso de falha.
            timeout: Timeout em segundos.
            condition: Condição para execução.

        Exemplo::

            @chain.step(retries=3, timeout=60)
            async def fetch_data(ctx: Context) -> Context:
                ...
        """
        def decorator(f: StepFunc) -> StepFunc:
            step_obj = Step(
                name=name or f.__name__,
                func=f,
                retries=retries,
                timeout=timeout,
                condition=condition,
            )
            self.steps.append(step_obj)
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def add_step(self, step: Step) -> None:
        """Adiciona um Step diretamente ao chain."""
        self.steps.append(step)

    async def run(self, ctx: Optional[Context] = None) -> Context:
        """Executa todos os steps em sequência.

        Args:
            ctx: Contexto inicial. Se None, cria um novo.

        Returns:
            Contexto final após todos os steps.

        Raises:
            PipelineError: Se algum step falhar.
        """
        if ctx is None:
            ctx = Context()

        results: list[StepResult] = []
        total_start = time.perf_counter()

        for step in self.steps:
            result = await step.execute(ctx)
            results.append(result)

        total_latency = (time.perf_counter() - total_start) * 1000
        ctx.metadata["chain_results"] = {
            "chain_name": self.name,
            "chain_id": self.chain_id,
            "total_steps": len(self.steps),
            "total_latency_ms": total_latency,
            "step_results": [r.model_dump() for r in results],
        }

        return ctx

    def __len__(self) -> int:
        return len(self.steps)

    def __repr__(self) -> str:
        return f"Chain(name={self.name!r}, steps={len(self.steps)})"
