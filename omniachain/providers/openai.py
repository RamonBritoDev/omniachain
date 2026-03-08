"""
OmniaChain — Provider OpenAI (GPT-4o, GPT-4 Turbo, etc.).

Exemplo::

    from omniachain.providers import OpenAI
    provider = OpenAI("gpt-4o")
    response = await provider.complete([Message.user("Olá GPT!")])
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Optional

from omniachain.core.config import get_config
from omniachain.core.errors import ProviderError
from omniachain.core.message import Message
from omniachain.core.response import Response, ToolCall, Usage
from omniachain.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Provider para modelos OpenAI (GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo).

    Exemplo::

        provider = OpenAIProvider("gpt-4o")
        result = await provider.complete([Message.user("Explique IA")])
    """

    MODEL_COSTS: dict[str, tuple[float, float]] = {
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-4": (0.03, 0.06),
        "gpt-3.5-turbo": (0.0005, 0.0015),
    }

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    @property
    def supports_vision(self) -> bool:
        return self.model in ("gpt-4o", "gpt-4o-mini", "gpt-4-turbo")

    @property
    def supports_tool_calling(self) -> bool:
        return True

    @property
    def cost_per_1k_tokens(self) -> tuple[float, float]:
        return self.MODEL_COSTS.get(self.model, (0.005, 0.015))

    def _get_client(self) -> Any:
        """Cria cliente OpenAI async."""
        try:
            import openai
        except ImportError:
            raise ProviderError(
                "Pacote 'openai' não instalado.",
                provider="openai",
                model=self.model,
                suggestion="Instale com: pip install openai",
            )

        api_key = self.api_key or get_config().openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError(
                "API key do OpenAI não configurada.",
                provider="openai",
                model=self.model,
                suggestion="Defina OPENAI_API_KEY no ambiente ou passe api_key=...",
            )

        return openai.AsyncOpenAI(
            api_key=api_key,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    def _format_tools_openai(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Converte tools para formato OpenAI."""
        result = []
        for t in tools:
            if "function" in t:
                result.append(t)
            else:
                result.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name", ""),
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {}),
                    },
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
        """Envia mensagens ao GPT e retorna resposta completa."""
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
                params["tools"] = self._format_tools_openai(tools)

            result = await client.chat.completions.create(**params)
            choice = result.choices[0]

            response.content = choice.message.content or ""
            response.finish_reason = choice.finish_reason

            # Tool calls
            if choice.message.tool_calls:
                import json
                for tc in choice.message.tool_calls:
                    response.tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                    ))

            # Usage
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
                f"Erro ao chamar OpenAI: {e}",
                provider="openai",
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
        """Streaming de tokens do GPT."""
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
                f"Erro no streaming OpenAI: {e}",
                provider="openai",
                model=self.model,
                original_error=e,
            )

    async def embed(self, text: str) -> list[float]:
        """Gera embedding usando text-embedding-3-small."""
        client = self._get_client()
        try:
            result = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return result.data[0].embedding
        except Exception as e:
            raise ProviderError(
                f"Erro ao gerar embedding OpenAI: {e}",
                provider="openai",
                model="text-embedding-3-small",
                original_error=e,
            )

    async def transcribe(self, audio: bytes, **kwargs: Any) -> str:
        """Transcreve áudio via OpenAI Whisper API."""
        import io

        client = self._get_client()
        try:
            audio_file = io.BytesIO(audio)
            audio_file.name = f"audio.{kwargs.get('format', 'mp3')}"
            transcript = await client.audio.transcriptions.create(
                model=kwargs.get("model", "whisper-1"),
                file=audio_file,
                language=kwargs.get("language", "pt"),
            )
            return transcript.text
        except Exception as e:
            raise ProviderError(
                f"Erro ao transcrever áudio OpenAI: {e}",
                provider="openai",
                model="whisper-1",
                original_error=e,
            )

    async def synthesize(self, text: str, **kwargs: Any) -> bytes:
        """Converte texto em áudio via OpenAI TTS API."""
        client = self._get_client()
        try:
            response = await client.audio.speech.create(
                model=kwargs.get("model", "tts-1"),
                voice=kwargs.get("voice", "nova"),
                input=text,
                response_format=kwargs.get("format", "mp3"),
            )
            return response.content
        except Exception as e:
            raise ProviderError(
                f"Erro ao sintetizar voz OpenAI: {e}",
                provider="openai",
                model="tts-1",
                original_error=e,
            )

    async def generate_image(self, prompt: str, **kwargs: Any) -> bytes:
        """Gera imagem via OpenAI DALL-E 3."""
        import base64 as b64

        client = self._get_client()
        try:
            response = await client.images.generate(
                model=kwargs.get("model", "dall-e-3"),
                prompt=prompt,
                size=kwargs.get("size", "1024x1024"),
                quality=kwargs.get("quality", "standard"),
                style=kwargs.get("style", "vivid"),
                response_format="b64_json",
                n=1,
            )
            b64_data = response.data[0].b64_json
            return b64.b64decode(b64_data) if b64_data else b""
        except Exception as e:
            raise ProviderError(
                f"Erro ao gerar imagem OpenAI: {e}",
                provider="openai",
                model="dall-e-3",
                original_error=e,
            )

    @property
    def supports_stt(self) -> bool:
        return True

    @property
    def supports_tts(self) -> bool:
        return True

    @property
    def supports_image_generation(self) -> bool:
        return True

