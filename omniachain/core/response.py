"""
OmniaChain — Resposta padronizada com metadados de execução.

Cada resposta inclui conteúdo, uso de tokens, custo estimado e metadados do provider.

Exemplo de uso::

    result = await agent.run("Qual a capital do Brasil?")
    print(result.content)        # "Brasília"
    print(result.usage.cost)     # 0.0012
    print(result.model)          # "claude-3-5-sonnet"
    print(result.latency_ms)     # 823.5
"""

from __future__ import annotations

import time
from typing import Any, Optional

from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Métricas de uso de tokens e custo.

    Exemplo::

        print(f"Tokens: {usage.total_tokens} | Custo: ${usage.cost:.4f}")
    """

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    cost_currency: str = "USD"

    def __add__(self, other: Usage) -> Usage:
        """Soma dois objetos Usage (útil para agregar múltiplas chamadas)."""
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost=self.cost + other.cost,
            cost_currency=self.cost_currency,
        )

    @classmethod
    def calculate(
        cls,
        input_tokens: int,
        output_tokens: int,
        cost_per_1k_input: float,
        cost_per_1k_output: float,
    ) -> Usage:
        """Calcula uso e custo a partir de contagem de tokens.

        Args:
            input_tokens: Número de tokens de entrada.
            output_tokens: Número de tokens de saída.
            cost_per_1k_input: Custo por 1000 tokens de entrada.
            cost_per_1k_output: Custo por 1000 tokens de saída.
        """
        cost = (input_tokens / 1000 * cost_per_1k_input) + (
            output_tokens / 1000 * cost_per_1k_output
        )
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=round(cost, 6),
        )


class ToolCall(BaseModel):
    """Representa uma chamada de tool feita pelo modelo.

    Attributes:
        id: Identificador único da chamada.
        name: Nome da tool chamada.
        arguments: Argumentos passados para a tool.
        result: Resultado da execução (preenchido após execução).
    """

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None


class Response(BaseModel):
    """Resposta padronizada de qualquer operação do OmniaChain.

    Exemplo::

        result = await agent.run("Pergunta")
        print(result.content)
        print(f"Latência: {result.latency_ms:.1f}ms")
        print(f"Custo: ${result.usage.cost:.4f}")
    """

    content: str = ""
    role: str = "assistant"
    usage: Usage = Field(default_factory=Usage)
    model: str = ""
    provider: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: Optional[str] = None
    trace_id: Optional[str] = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    _start_time: Optional[float] = None

    def start_timer(self) -> None:
        """Inicia o timer de latência."""
        self._start_time = time.perf_counter()

    def stop_timer(self) -> None:
        """Para o timer e calcula latência em ms."""
        if self._start_time is not None:
            self.latency_ms = (time.perf_counter() - self._start_time) * 1000
            self._start_time = None

    @property
    def has_tool_calls(self) -> bool:
        """Retorna True se a resposta contém chamadas de tool."""
        return len(self.tool_calls) > 0

    @property
    def is_complete(self) -> bool:
        """Retorna True se a resposta está completa (stop ou end_turn)."""
        return self.finish_reason in ("stop", "end_turn", "length")

    def __str__(self) -> str:
        return self.content

    model_config = {"arbitrary_types_allowed": True}
