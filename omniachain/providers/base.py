"""
OmniaChain — Interface base unificada para providers de IA.

Define o contrato que todos os providers (Anthropic, OpenAI, Groq, etc.) devem implementar.

Exemplo::

    class MeuProvider(BaseProvider):
        async def complete(self, messages, **kwargs) -> Response: ...
        async def stream(self, messages, **kwargs) -> AsyncGenerator[str, None]: ...
"""

from __future__ import annotations

import abc
from typing import Any, AsyncGenerator, Optional

from omniachain.core.message import Message
from omniachain.core.response import Response


class BaseProvider(abc.ABC):
    """Interface unificada que todos os providers de IA devem implementar.

    Cada provider deve fornecer:
    - complete(): Chamada síncrona que retorna resposta completa
    - stream(): Chamada streaming que retorna tokens incrementalmente
    - embed(): Gera embeddings vetoriais de texto
    - Propriedades de capacidade e custo

    Exemplo::

        provider = Anthropic("claude-3-5-sonnet-20241022")
        response = await provider.complete([Message.user("Olá!")])
        print(response.content)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        self.model = model or self.default_model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_config = kwargs

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Nome do provider (ex: 'anthropic', 'openai')."""
        ...

    @property
    @abc.abstractmethod
    def default_model(self) -> str:
        """Modelo padrão quando nenhum é especificado."""
        ...

    @abc.abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Response:
        """Envia mensagens e retorna resposta completa.

        Args:
            messages: Lista de mensagens da conversa.
            temperature: Criatividade (0.0 = determinístico, 1.0 = criativo).
            max_tokens: Máximo de tokens na resposta.
            tools: Definições de tools disponíveis (JSON schema).
            **kwargs: Parâmetros extras do provider.

        Returns:
            Response com conteúdo, usage e metadados.
        """
        ...

    @abc.abstractmethod
    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Envia mensagens e retorna tokens via streaming.

        Args:
            messages: Lista de mensagens da conversa.
            temperature: Criatividade.
            max_tokens: Máximo de tokens na resposta.
            **kwargs: Parâmetros extras.

        Yields:
            str: Tokens individuais conforme são gerados.
        """
        ...
        yield ""  # pragma: no cover

    async def embed(self, text: str) -> list[float]:
        """Gera embedding vetorial de um texto.

        Args:
            text: Texto para gerar embedding.

        Returns:
            Lista de floats representando o vetor.

        Raises:
            NotImplementedError: Se o provider não suporta embeddings.
        """
        raise NotImplementedError(
            f"Provider '{self.provider_name}' não suporta embeddings."
        )

    async def transcribe(self, audio: bytes, **kwargs: Any) -> str:
        """Transcreve áudio para texto (STT).

        Args:
            audio: Bytes do áudio.
            **kwargs: format, language, etc.

        Returns:
            Texto transcrito.

        Raises:
            NotImplementedError: Se o provider não suporta STT.
        """
        raise NotImplementedError(
            f"Provider '{self.provider_name}' não suporta STT (Speech-to-Text)."
        )

    async def synthesize(self, text: str, **kwargs: Any) -> bytes:
        """Converte texto em áudio (TTS).

        Args:
            text: Texto para sintetizar.
            **kwargs: voice, format, etc.

        Returns:
            Bytes do áudio gerado.

        Raises:
            NotImplementedError: Se o provider não suporta TTS.
        """
        raise NotImplementedError(
            f"Provider '{self.provider_name}' não suporta TTS (Text-to-Speech)."
        )

    async def generate_image(self, prompt: str, **kwargs: Any) -> bytes:
        """Gera imagem a partir de prompt.

        Args:
            prompt: Descrição da imagem.
            **kwargs: size, quality, style, etc.

        Returns:
            Bytes da imagem gerada.

        Raises:
            NotImplementedError: Se o provider não suporta geração de imagens.
        """
        raise NotImplementedError(
            f"Provider '{self.provider_name}' não suporta geração de imagens."
        )

    @property
    def supports_stt(self) -> bool:
        """Retorna True se o provider suporta Speech-to-Text."""
        return False

    @property
    def supports_tts(self) -> bool:
        """Retorna True se o provider suporta Text-to-Speech."""
        return False

    @property
    def supports_image_generation(self) -> bool:
        """Retorna True se o provider suporta geração de imagens."""
        return False

    @property
    @abc.abstractmethod
    def supports_vision(self) -> bool:
        """Retorna True se o provider/modelo suporta imagens."""
        ...

    @property
    @abc.abstractmethod
    def supports_tool_calling(self) -> bool:
        """Retorna True se o provider/modelo suporta tool calling."""
        ...

    @property
    @abc.abstractmethod
    def cost_per_1k_tokens(self) -> tuple[float, float]:
        """Custo por 1000 tokens: (input, output) em USD."""
        ...

    def _format_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Converte mensagens OmniaChain para o formato do provider.

        Esta implementação base converte para o formato OpenAI-like.
        Providers com formato diferente devem sobrescrever.
        """
        formatted: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.role.value

            # Mensagens de resultado de tool
            if role == "tool":
                tool_call_id = msg.content[0].metadata.get("tool_call_id", "") if msg.content else ""
                formatted.append({
                    "role": "tool",
                    "content": msg.text,
                    "tool_call_id": tool_call_id,
                })

            # Mensagens de assistant com tool_calls
            elif role == "assistant" and msg.metadata.get("tool_calls"):
                entry: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.text or None,
                    "tool_calls": msg.metadata["tool_calls"],
                }
                formatted.append(entry)

            # Mensagens com conteúdo binário (imagens, etc.)
            elif msg.has_binary:
                content_parts: list[dict[str, Any]] = []
                for c in msg.content:
                    if c.type.value == "text":
                        content_parts.append({"type": "text", "text": str(c.data)})
                    elif c.type.value == "image":
                        if isinstance(c.data, str) and c.data.startswith(("http://", "https://")):
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": c.data},
                            })
                        else:
                            mime = c.mime_type or "image/png"
                            if isinstance(c.data, bytes):
                                import base64
                                b64 = base64.b64encode(c.data).decode()
                            else:
                                # Já é string — pode ser base64
                                b64 = str(c.data)
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{b64}"
                                },
                            })
                formatted.append({"role": role, "content": content_parts})
            else:
                formatted.append({"role": role, "content": msg.text})
        return formatted

    def __repr__(self) -> str:
        return f"{type(self).__name__}(model={self.model!r})"
