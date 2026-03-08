"""
OmniaChain — Provider Ollama (modelos locais).

Exemplo::

    from omniachain.providers import Ollama
    provider = Ollama("llama3.1")  # Modelo rodando localmente
    response = await provider.complete([Message.user("Olá!")])
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Optional

import httpx

from omniachain.core.config import get_config
from omniachain.core.errors import ProviderError
from omniachain.core.message import Message
from omniachain.core.response import Response, Usage
from omniachain.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    """Provider para modelos locais via Ollama.

    Não requer API key — conecta ao servidor Ollama local.

    Exemplo::

        provider = OllamaProvider("llama3.1")
        result = await provider.complete([Message.user("Explique IA")])
    """

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return "llama3.1"

    @property
    def supports_vision(self) -> bool:
        return self.model in ("llava", "llava:13b", "bakllava", "moondream")

    @property
    def supports_tool_calling(self) -> bool:
        return False

    @property
    def cost_per_1k_tokens(self) -> tuple[float, float]:
        return (0.0, 0.0)  # Modelos locais = custo zero

    def _get_base_url(self) -> str:
        """Retorna URL base do Ollama."""
        return self.base_url or get_config().ollama_base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Response:
        """Envia mensagens ao Ollama local e retorna resposta completa."""
        base_url = self._get_base_url()
        formatted = self._format_messages(messages)

        response = Response(model=self.model, provider=self.provider_name)
        response.start_timer()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                result = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": formatted,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                result.raise_for_status()
                data = result.json()

            response.content = data.get("message", {}).get("content", "")
            response.finish_reason = "stop"

            # Usage
            if "eval_count" in data:
                response.usage = Usage(
                    input_tokens=data.get("prompt_eval_count", 0),
                    output_tokens=data.get("eval_count", 0),
                    total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    cost=0.0,
                )

        except httpx.ConnectError:
            raise ProviderError(
                "Não foi possível conectar ao Ollama.",
                provider="ollama",
                model=self.model,
                suggestion=f"Verifique se o Ollama está rodando em {base_url}. Inicie com: ollama serve",
            )
        except Exception as e:
            raise ProviderError(
                f"Erro ao chamar Ollama: {e}",
                provider="ollama",
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
        """Streaming de tokens do Ollama local."""
        base_url = self._get_base_url()
        formatted = self._format_messages(messages)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": formatted,
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                ) as resp:
                    import json
                    async for line in resp.aiter_lines():
                        if line:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done", False):
                                break

        except httpx.ConnectError:
            raise ProviderError(
                "Não foi possível conectar ao Ollama para streaming.",
                provider="ollama",
                model=self.model,
                suggestion=f"Verifique se o Ollama está rodando em {base_url}.",
            )
        except Exception as e:
            raise ProviderError(
                f"Erro no streaming Ollama: {e}",
                provider="ollama",
                model=self.model,
                original_error=e,
            )

    async def embed(self, text: str) -> list[float]:
        """Gera embedding usando modelo local do Ollama."""
        base_url = self._get_base_url()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                result = await client.post(
                    f"{base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                result.raise_for_status()
                return result.json().get("embedding", [])
        except Exception as e:
            raise ProviderError(
                f"Erro ao gerar embedding via Ollama: {e}",
                provider="ollama",
                model=self.model,
                original_error=e,
            )
