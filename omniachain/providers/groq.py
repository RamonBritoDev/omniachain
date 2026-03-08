"""
OmniaChain — Provider Groq (Llama 3, Mixtral — inference ultra-rápida).

Exemplo::

    from omniachain.providers import Groq
    provider = Groq("llama-3.1-70b-versatile")
    response = await provider.complete([Message.user("Olá Llama!")])
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Optional

from omniachain.core.config import get_config
from omniachain.core.errors import ProviderError
from omniachain.core.message import Message
from omniachain.core.response import Response, ToolCall, Usage
from omniachain.providers.base import BaseProvider


class GroqProvider(BaseProvider):
    """Provider para modelos via Groq (Llama 3, Mixtral com inference ultrarrápida).

    Exemplo::

        provider = GroqProvider("llama-3.1-70b-versatile")
        result = await provider.complete([Message.user("Explique IA")])
    """

    MODEL_COSTS: dict[str, tuple[float, float]] = {
        "llama-3.1-70b-versatile": (0.00059, 0.00079),
        "llama-3.1-8b-instant": (0.00005, 0.00008),
        "llama-3.3-70b-versatile": (0.00059, 0.00079),
        "mixtral-8x7b-32768": (0.00024, 0.00024),
        "gemma2-9b-it": (0.00020, 0.00020),
    }

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def default_model(self) -> str:
        return "llama-3.3-70b-versatile"

    @property
    def supports_vision(self) -> bool:
        return False

    @property
    def supports_tool_calling(self) -> bool:
        return True

    @property
    def cost_per_1k_tokens(self) -> tuple[float, float]:
        return self.MODEL_COSTS.get(self.model, (0.00059, 0.00079))

    def _get_client(self) -> Any:
        """Cria cliente Groq async."""
        try:
            import groq
        except ImportError:
            raise ProviderError(
                "Pacote 'groq' não instalado.",
                provider="groq",
                model=self.model,
                suggestion="Instale com: pip install groq",
            )

        api_key = self.api_key or get_config().groq_api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ProviderError(
                "API key do Groq não configurada.",
                provider="groq",
                model=self.model,
                suggestion="Defina GROQ_API_KEY no ambiente ou passe api_key=...",
            )

        return groq.AsyncGroq(api_key=api_key, timeout=self.timeout, max_retries=self.max_retries)

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Response:
        """Envia mensagens ao Groq e retorna resposta completa."""
        client = self._get_client()
        formatted = self._format_messages(messages)

        response = Response(model=self.model, provider=self.provider_name)
        response.start_timer()

        try:
            params: dict[str, Any] = {
                "model": self.model,
                "messages": formatted,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if tools:
                params["tools"] = tools

            result = await client.chat.completions.create(**params)
            choice = result.choices[0]

            response.content = choice.message.content or ""
            response.finish_reason = choice.finish_reason

            if choice.message.tool_calls:
                import json
                for tc in choice.message.tool_calls:
                    response.tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                    ))

            if result.usage:
                input_cost, output_cost = self.cost_per_1k_tokens
                response.usage = Usage.calculate(
                    input_tokens=result.usage.prompt_tokens,
                    output_tokens=result.usage.completion_tokens,
                    cost_per_1k_input=input_cost,
                    cost_per_1k_output=output_cost,
                )

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Erro ao chamar Groq: {e}",
                provider="groq",
                model=self.model,
                original_error=e,
            )
        finally:
            response.stop_timer()

        return response

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Streaming de tokens via Groq."""
        client = self._get_client()
        formatted = self._format_messages(messages)

        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=formatted,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise ProviderError(
                f"Erro no streaming Groq: {e}",
                provider="groq",
                model=self.model,
                original_error=e,
            )
