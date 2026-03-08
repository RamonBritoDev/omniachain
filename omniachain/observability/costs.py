"""OmniaChain — CostTracker: tracking de tokens e custos em tempo real."""

from __future__ import annotations

import time
from typing import Any
from pydantic import BaseModel, Field

from omniachain.core.response import Usage


class CostEntry(BaseModel):
    """Entrada individual de custo."""
    provider: str
    model: str
    usage: Usage
    timestamp: float = Field(default_factory=time.time)
    operation: str = "complete"


class CostTracker:
    """Rastreia custos de tokens em tempo real.

    Exemplo::

        tracker = CostTracker()
        tracker.record(response)
        print(f"Custo total: ${tracker.total_cost:.4f}")
        print(tracker.summary())
    """

    def __init__(self) -> None:
        self._entries: list[CostEntry] = []

    def record(self, response: Any) -> None:
        """Registra o custo de uma resposta."""
        from omniachain.core.response import Response
        if isinstance(response, Response):
            self._entries.append(CostEntry(
                provider=response.provider,
                model=response.model,
                usage=response.usage,
                operation="complete",
            ))

    def record_usage(self, provider: str, model: str, usage: Usage, operation: str = "complete") -> None:
        """Registra uso diretamente."""
        self._entries.append(CostEntry(provider=provider, model=model, usage=usage, operation=operation))

    @property
    def total_cost(self) -> float:
        return sum(e.usage.cost for e in self._entries)

    @property
    def total_tokens(self) -> int:
        return sum(e.usage.total_tokens for e in self._entries)

    @property
    def total_input_tokens(self) -> int:
        return sum(e.usage.input_tokens for e in self._entries)

    @property
    def total_output_tokens(self) -> int:
        return sum(e.usage.output_tokens for e in self._entries)

    def by_provider(self) -> dict[str, dict[str, Any]]:
        """Agrupa custos por provider."""
        result: dict[str, dict[str, Any]] = {}
        for e in self._entries:
            if e.provider not in result:
                result[e.provider] = {"cost": 0.0, "tokens": 0, "calls": 0}
            result[e.provider]["cost"] += e.usage.cost
            result[e.provider]["tokens"] += e.usage.total_tokens
            result[e.provider]["calls"] += 1
        return result

    def by_model(self) -> dict[str, dict[str, Any]]:
        """Agrupa custos por modelo."""
        result: dict[str, dict[str, Any]] = {}
        for e in self._entries:
            if e.model not in result:
                result[e.model] = {"cost": 0.0, "tokens": 0, "calls": 0}
            result[e.model]["cost"] += e.usage.cost
            result[e.model]["tokens"] += e.usage.total_tokens
            result[e.model]["calls"] += 1
        return result

    def summary(self) -> str:
        """Retorna resumo legível dos custos."""
        lines = [
            f"═══ OmniaChain Cost Summary ═══",
            f"Total: ${self.total_cost:.4f} | {self.total_tokens:,} tokens | {len(self._entries)} chamadas",
            f"Input: {self.total_input_tokens:,} | Output: {self.total_output_tokens:,}",
            "",
        ]
        for provider, data in self.by_provider().items():
            lines.append(f"  {provider}: ${data['cost']:.4f} ({data['calls']} chamadas)")
        return "\n".join(lines)

    def reset(self) -> None:
        """Limpa todos os registros."""
        self._entries.clear()
