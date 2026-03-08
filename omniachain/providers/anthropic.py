"""
OmniaChain — Provider Anthropic (Claude).

Suporta Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku com tool calling e visão.

Exemplo::

    from omniachain.providers import Anthropic

    provider = Anthropic()  # Usa ANTHROPIC_API_KEY do env
    response = await provider.complete([Message.user("Olá Claude!")])
    print(response.content)
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Optional

from omniachain.core.config import get_config
from omniachain.core.errors import ProviderError
from omniachain.core.message import Message
from omniachain.core.response import Response, ToolCall, Usage
from omniachain.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Provider para modelos Anthropic Claude.

    Suporta Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku.
    Detecta ANTHROPIC_API_KEY do ambiente automaticamente.

    Exemplo::

        provider = AnthropicProvider("claude-3-5-sonnet-20241022")
        result = await provider.complete([Message.user("Explique IA")])
    """

    MODEL_COSTS: dict[str, tuple[float, float]] = {
        "claude-sonnet-4-20250514": (0.003, 0.015),
        "claude-3-5-sonnet-20241022": (0.003, 0.015),
        "claude-3-5-sonnet-20240620": (0.003, 0.015),
        "claude-3-opus-20240229": (0.015, 0.075),
        "claude-3-haiku-20240307": (0.00025, 0.00125),
    }

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    @property
    def supports_vision(self) -> bool:
        return True

    @property
    def supports_tool_calling(self) -> bool:
        return True

    @property
    def cost_per_1k_tokens(self) -> tuple[float, float]:
        return self.MODEL_COSTS.get(self.model, (0.003, 0.015))

    def _get_client(self) -> Any:
        """Cria cliente Anthropic com lazy import."""
        try:
            import anthropic
        except ImportError:
            raise ProviderError(
                "Pacote 'anthropic' não instalado.",
                provider="anthropic",
                model=self.model,
                suggestion="Instale com: pip install anthropic",
            )

        api_key = self.api_key or get_config().anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError(
                "API key do Anthropic não configurada.",
                provider="anthropic",
                model=self.model,
                suggestion="Defina ANTHROPIC_API_KEY no ambiente ou passe api_key=...",
            )

        return anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    def _format_messages_anthropic(
        self, messages: list[Message]
    ) -> tuple[Optional[str], list[dict[str, Any]]]:
        """Converte mensagens para formato Anthropic (system separado)."""
        system_text: Optional[str] = None
        formatted: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role.value == "system":
                system_text = msg.text
                continue

            if msg.has_binary:
                content_parts: list[dict[str, Any]] = []
                for c in msg.content:
                    if c.type.value == "text":
                        content_parts.append({"type": "text", "text": str(c.data)})
                    elif c.type.value == "image":
                        import base64 as b64module
                        if isinstance(c.data, bytes):
                            data_b64 = b64module.b64encode(c.data).decode()
                        elif isinstance(c.data, str) and c.data.startswith(("http://", "https://")):
                            content_parts.append({
                                "type": "image",
                                "source": {"type": "url", "url": c.data},
                            })
                            continue
                        else:
                            data_b64 = str(c.data)
                        content_parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": c.mime_type or "image/png",
                                "data": data_b64,
                            },
                        })
                formatted.append({"role": msg.role.value, "content": content_parts})
            else:
                role = "user" if msg.role.value == "tool" else msg.role.value
                formatted.append({"role": role, "content": msg.text})

        return system_text, formatted

    def _format_tools_anthropic(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Converte definições de tools para formato Anthropic."""
        result = []
        for t in tools:
            result.append({
                "name": t.get("name", t.get("function", {}).get("name", "")),
                "description": t.get("description", t.get("function", {}).get("description", "")),
                "input_schema": t.get("parameters", t.get("function", {}).get("parameters", {})),
            })
        return result

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Response:
        """Envia mensagens ao Claude e retorna resposta completa."""
        client = self._get_client()
        system_text, formatted = self._format_messages_anthropic(messages)

        response = Response(model=self.model, provider=self.provider_name)
        response.start_timer()

        try:
            params: dict[str, Any] = {
                "model": self.model,
                "messages": formatted,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_text:
                params["system"] = system_text
            if tools:
                params["tools"] = self._format_tools_anthropic(tools)

            result = await client.messages.create(**params)

            # Processar resposta
            content_parts: list[str] = []
            tool_calls: list[ToolCall] = []

            for block in result.content:
                if block.type == "text":
                    content_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=dict(block.input) if block.input else {},
                    ))

            response.content = "\n".join(content_parts)
            response.tool_calls = tool_calls
            response.finish_reason = result.stop_reason

            # Usage
            input_cost, output_cost = self.cost_per_1k_tokens
            response.usage = Usage.calculate(
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                cost_per_1k_input=input_cost,
                cost_per_1k_output=output_cost,
            )

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Erro ao chamar Anthropic: {e}",
                provider="anthropic",
                model=self.model,
                suggestion="Verifique sua API key e conexão com a API.",
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
        """Streaming de tokens do Claude."""
        client = self._get_client()
        system_text, formatted = self._format_messages_anthropic(messages)

        try:
            params: dict[str, Any] = {
                "model": self.model,
                "messages": formatted,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_text:
                params["system"] = system_text

            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            raise ProviderError(
                f"Erro no streaming Anthropic: {e}",
                provider="anthropic",
                model=self.model,
                original_error=e,
            )
