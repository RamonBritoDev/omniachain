"""
OmniaChain — Provider Google (Gemini 1.5 Pro, Flash).

Exemplo::

    from omniachain.providers import Google
    provider = Google("gemini-1.5-pro")
    response = await provider.complete([Message.user("Olá Gemini!")])
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Optional

from omniachain.core.config import get_config
from omniachain.core.errors import ProviderError
from omniachain.core.message import Message
from omniachain.core.response import Response, Usage
from omniachain.providers.base import BaseProvider


class GoogleProvider(BaseProvider):
    """Provider para Google Gemini (1.5 Pro, 1.5 Flash, etc.).

    Exemplo::

        provider = GoogleProvider("gemini-1.5-pro")
        result = await provider.complete([Message.user("Explique IA")])
    """

    MODEL_COSTS: dict[str, tuple[float, float]] = {
        "gemini-1.5-pro": (0.00125, 0.005),
        "gemini-1.5-flash": (0.000075, 0.0003),
        "gemini-2.0-flash": (0.0001, 0.0004),
        "gemini-2.5-pro": (0.00125, 0.01),
    }

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def default_model(self) -> str:
        return "gemini-2.0-flash"

    @property
    def supports_vision(self) -> bool:
        return True

    @property
    def supports_tool_calling(self) -> bool:
        return True

    @property
    def cost_per_1k_tokens(self) -> tuple[float, float]:
        return self.MODEL_COSTS.get(self.model, (0.00125, 0.005))

    def _get_client(self) -> Any:
        """Configura e retorna o GenerativeModel."""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ProviderError(
                "Pacote 'google-generativeai' não instalado.",
                provider="google",
                model=self.model,
                suggestion="Instale com: pip install google-generativeai",
            )

        api_key = self.api_key or get_config().google_api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ProviderError(
                "API key do Google não configurada.",
                provider="google",
                model=self.model,
                suggestion="Defina GOOGLE_API_KEY no ambiente ou passe api_key=...",
            )

        genai.configure(api_key=api_key)
        return genai.GenerativeModel(self.model)

    def _format_messages_google(self, messages: list[Message]) -> tuple[Optional[str], list[dict[str, Any]]]:
        """Converte mensagens para formato Google (system_instruction separado)."""
        system_text: Optional[str] = None
        history: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role.value == "system":
                system_text = msg.text
                continue

            role = "user" if msg.role.value in ("user", "tool") else "model"
            parts: list[Any] = []

            for c in msg.content:
                if c.type.value == "text":
                    parts.append(str(c.data))
                elif c.type.value == "image" and isinstance(c.data, bytes):
                    parts.append({
                        "mime_type": c.mime_type or "image/png",
                        "data": c.data,
                    })

            if parts:
                history.append({"role": role, "parts": parts})

        return system_text, history

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Response:
        """Envia mensagens ao Gemini e retorna resposta completa."""
        import asyncio

        model = self._get_client()
        system_text, history = self._format_messages_google(messages)

        response = Response(model=self.model, provider=self.provider_name)
        response.start_timer()

        try:
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            # Extrair última mensagem como prompt, resto como history
            if history:
                last_msg = history[-1]
                chat_history = history[:-1] if len(history) > 1 else []

                chat = model.start_chat(history=chat_history)
                result = await asyncio.to_thread(
                    chat.send_message,
                    last_msg["parts"],
                    generation_config=generation_config,
                )
            else:
                result = await asyncio.to_thread(
                    model.generate_content,
                    "Hello",
                    generation_config=generation_config,
                )

            response.content = result.text or ""
            response.finish_reason = "stop"

            # Usage
            if hasattr(result, "usage_metadata") and result.usage_metadata:
                input_cost, output_cost = self.cost_per_1k_tokens
                prompt_tokens = getattr(result.usage_metadata, "prompt_token_count", 0) or 0
                completion_tokens = getattr(result.usage_metadata, "candidates_token_count", 0) or 0
                response.usage = Usage.calculate(
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    cost_per_1k_input=input_cost,
                    cost_per_1k_output=output_cost,
                )

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(
                f"Erro ao chamar Google Gemini: {e}",
                provider="google",
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
        """Streaming de tokens do Gemini."""
        import asyncio

        model = self._get_client()
        system_text, history = self._format_messages_google(messages)

        try:
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }

            if history:
                last_msg = history[-1]
                chat_history = history[:-1] if len(history) > 1 else []
                chat = model.start_chat(history=chat_history)

                result = await asyncio.to_thread(
                    chat.send_message,
                    last_msg["parts"],
                    generation_config=generation_config,
                    stream=True,
                )

                for chunk in result:
                    if chunk.text:
                        yield chunk.text

        except Exception as e:
            raise ProviderError(
                f"Erro no streaming Google Gemini: {e}",
                provider="google",
                model=self.model,
                original_error=e,
            )

    async def embed(self, text: str) -> list[float]:
        """Gera embedding usando Gemini."""
        import asyncio

        try:
            import google.generativeai as genai

            api_key = self.api_key or get_config().google_api_key or os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=api_key)

            result = await asyncio.to_thread(
                genai.embed_content,
                model="models/text-embedding-004",
                content=text,
            )
            return result["embedding"]
        except Exception as e:
            raise ProviderError(
                f"Erro ao gerar embedding Google: {e}",
                provider="google",
                model="text-embedding-004",
                original_error=e,
            )

    async def transcribe(self, audio: bytes, **kwargs: Any) -> str:
        """Transcreve áudio usando Gemini (envia áudio como input multimodal)."""
        import asyncio

        try:
            import google.generativeai as genai

            api_key = self.api_key or get_config().google_api_key or os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(self.model)
            audio_format = kwargs.get("format", "mp3")
            mime_type = f"audio/{audio_format}"

            result = await asyncio.to_thread(
                model.generate_content,
                [
                    "Transcreva o seguinte áudio fielmente, retornando apenas o texto:",
                    {"mime_type": mime_type, "data": audio},
                ],
            )
            return result.text or ""
        except Exception as e:
            raise ProviderError(
                f"Erro ao transcrever áudio via Google Gemini: {e}",
                provider="google",
                model=self.model,
                original_error=e,
            )

    async def generate_image(self, prompt: str, **kwargs: Any) -> bytes:
        """Gera imagem via Google Gemini Nano Banana."""
        import asyncio

        try:
            import google.generativeai as genai

            api_key = self.api_key or get_config().google_api_key or os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=api_key)

            model_name = kwargs.get("model", "gemini-2.0-flash-exp-image-generation")
            model = genai.GenerativeModel(model_name)

            result = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            for part in result.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return part.inline_data.data

            return b""
        except Exception as e:
            raise ProviderError(
                f"Erro ao gerar imagem via Google Nano Banana: {e}",
                provider="google",
                model="nano-banana",
                original_error=e,
            )

    @property
    def supports_stt(self) -> bool:
        return True

    @property
    def supports_image_generation(self) -> bool:
        return True

