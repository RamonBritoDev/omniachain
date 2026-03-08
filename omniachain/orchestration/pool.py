"""OmniaChain — ProviderPool: pool de providers com fallback."""

from __future__ import annotations

from typing import Any, Literal, Optional

from omniachain.core.errors import ProviderError
from omniachain.core.message import Message
from omniachain.core.response import Response
from omniachain.providers.base import BaseProvider


class ProviderPool:
    """Pool de providers com fallback, round-robin e seleção por custo.

    Exemplo::

        pool = ProviderPool([Anthropic(), OpenAI(), Groq()], strategy="fallback")
        response = await pool.complete(messages)
    """

    def __init__(
        self,
        providers: list[BaseProvider],
        strategy: Literal["fallback", "round_robin", "cheapest", "fastest"] = "fallback",
    ) -> None:
        self.providers = providers
        self.strategy = strategy
        self._rr_index = 0
        self._latencies: dict[str, float] = {}

    async def complete(self, messages: list[Message], **kwargs: Any) -> Response:
        """Envia para provider usando a estratégia configurada."""
        ordered = self._get_ordered_providers()
        errors: list[str] = []

        for provider in ordered:
            try:
                response = await provider.complete(messages, **kwargs)
                self._latencies[provider.provider_name] = response.latency_ms
                response.metadata["pool_strategy"] = self.strategy
                return response
            except Exception as e:
                errors.append(f"{provider.provider_name}: {e}")
                continue

        raise ProviderError(
            f"Todos os providers falharam: {'; '.join(errors)}",
            provider="pool",
            suggestion="Verifique as API keys e conectividade de pelo menos um provider.",
        )

    def _get_ordered_providers(self) -> list[BaseProvider]:
        """Ordena providers conforme a estratégia."""
        if self.strategy == "fallback":
            return list(self.providers)

        elif self.strategy == "round_robin":
            idx = self._rr_index % len(self.providers)
            self._rr_index += 1
            return self.providers[idx:] + self.providers[:idx]

        elif self.strategy == "cheapest":
            return sorted(self.providers, key=lambda p: sum(p.cost_per_1k_tokens))

        elif self.strategy == "fastest":
            def _latency(p: BaseProvider) -> float:
                return self._latencies.get(p.provider_name, float("inf"))
            return sorted(self.providers, key=_latency)

        return list(self.providers)
