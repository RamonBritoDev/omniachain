"""OmniaChain — CostOptimizer: escolhe provider mais barato por tarefa."""

from __future__ import annotations

from typing import Any, Optional

from omniachain.providers.base import BaseProvider


class CostOptimizer:
    """Optimiza custos selecionando o provider mais barato capaz de executar a tarefa.

    Exemplo::

        optimizer = CostOptimizer(providers)
        provider = optimizer.select(needs_vision=False, max_cost=0.001)
    """

    def __init__(self, providers: list[BaseProvider]) -> None:
        self.providers = providers
        self._usage_history: list[dict[str, Any]] = []

    def select(
        self,
        *,
        needs_vision: bool = False,
        needs_tools: bool = False,
        max_cost_per_1k: Optional[float] = None,
        prefer_local: bool = False,
    ) -> BaseProvider:
        """Seleciona o provider mais barato que atende aos requisitos.

        Args:
            needs_vision: Se True, exige suporte a visão.
            needs_tools: Se True, exige suporte a tool calling.
            max_cost_per_1k: Custo máximo por 1k tokens (input + output).
            prefer_local: Se True, preferir modelos locais (custo zero).
        """
        candidates = self.providers[:]

        if needs_vision:
            candidates = [p for p in candidates if p.supports_vision]
        if needs_tools:
            candidates = [p for p in candidates if p.supports_tool_calling]
        if max_cost_per_1k:
            candidates = [p for p in candidates if sum(p.cost_per_1k_tokens) <= max_cost_per_1k]

        if not candidates:
            # Fallback: retorna o primeiro available
            return self.providers[0]

        if prefer_local:
            local = [p for p in candidates if p.provider_name == "ollama"]
            if local:
                return local[0]

        # Ordenar por custo (input + output)
        return sorted(candidates, key=lambda p: sum(p.cost_per_1k_tokens))[0]

    def estimate_cost(self, provider: BaseProvider, input_tokens: int, output_tokens: int) -> float:
        """Estima o custo de uma chamada."""
        input_cost, output_cost = provider.cost_per_1k_tokens
        return (input_tokens / 1000 * input_cost) + (output_tokens / 1000 * output_cost)

    def get_cost_ranking(self) -> list[dict[str, Any]]:
        """Retorna ranking de providers por custo."""
        return sorted(
            [{"provider": p.provider_name, "model": p.model, "cost_per_1k": sum(p.cost_per_1k_tokens)} for p in self.providers],
            key=lambda x: x["cost_per_1k"],
        )
