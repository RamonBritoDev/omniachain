"""
OmniaChain — Estrutura universal de mensagem multi-modal.

Suporta texto, imagem, áudio, vídeo, documentos, tabelas, código e base64, 
tudo em uma única interface unificada.

Exemplo de uso::

    msg = Message.user("Analise esta imagem", ImageContent(path="foto.png"))
    msg2 = Message.system("Você é um assistente de IA.")
    msg3 = Message.assistant("Claro, vou analisar.")
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Tipos de conteúdo suportados pelo OmniaChain."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    TABLE = "table"
    CODE = "code"
    BASE64 = "base64"


class Role(str, Enum):
    """Papéis possíveis em uma conversa."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageContent(BaseModel):
    """Conteúdo individual de uma mensagem.

    Cada mensagem pode conter múltiplos conteúdos (texto + imagem, etc.).

    Attributes:
        type: Tipo do conteúdo (text, image, audio, etc.).
        data: Dados brutos — pode ser str, bytes, dict, DataFrame, etc.
        mime_type: MIME type quando aplicável (image/png, audio/mp3, etc.).
        metadata: Metadados adicionais (filename, encoding, dimensions, etc.).

    Exemplo::

        text = MessageContent(type=ContentType.TEXT, data="Olá mundo")
        img = MessageContent(type=ContentType.IMAGE, data=b"...", mime_type="image/png")
    """

    type: ContentType
    data: Any
    mime_type: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def text(cls, content: str) -> MessageContent:
        """Cria conteúdo de texto simples."""
        return cls(type=ContentType.TEXT, data=content)

    @classmethod
    def image(
        cls, data: Union[str, bytes], mime_type: str = "image/png", **metadata: Any
    ) -> MessageContent:
        """Cria conteúdo de imagem.

        Args:
            data: Caminho do arquivo ou bytes raw da imagem.
            mime_type: MIME type da imagem.
            **metadata: Metadados adicionais (width, height, etc.).
        """
        return cls(type=ContentType.IMAGE, data=data, mime_type=mime_type, metadata=metadata)

    @classmethod
    def audio(
        cls, data: Union[str, bytes], mime_type: str = "audio/mp3", **metadata: Any
    ) -> MessageContent:
        """Cria conteúdo de áudio."""
        return cls(type=ContentType.AUDIO, data=data, mime_type=mime_type, metadata=metadata)

    @classmethod
    def video(
        cls, data: Union[str, bytes], mime_type: str = "video/mp4", **metadata: Any
    ) -> MessageContent:
        """Cria conteúdo de vídeo."""
        return cls(type=ContentType.VIDEO, data=data, mime_type=mime_type, metadata=metadata)

    @classmethod
    def document(cls, data: Union[str, bytes], filename: str = "", **metadata: Any) -> MessageContent:
        """Cria conteúdo de documento (PDF, etc.)."""
        meta = {"filename": filename, **metadata}
        return cls(type=ContentType.DOCUMENT, data=data, mime_type="application/pdf", metadata=meta)

    @classmethod
    def table(cls, data: Any, **metadata: Any) -> MessageContent:
        """Cria conteúdo tabular (DataFrame, lista de dicts, etc.)."""
        return cls(type=ContentType.TABLE, data=data, metadata=metadata)

    @classmethod
    def code(
        cls, source: str, language: str = "python", **metadata: Any
    ) -> MessageContent:
        """Cria conteúdo de código fonte."""
        meta = {"language": language, **metadata}
        return cls(type=ContentType.CODE, data=source, metadata=meta)

    @classmethod
    def from_base64(
        cls, data: str, mime_type: str = "application/octet-stream", **metadata: Any
    ) -> MessageContent:
        """Cria conteúdo a partir de dados base64."""
        return cls(type=ContentType.BASE64, data=data, mime_type=mime_type, metadata=metadata)

    def is_binary(self) -> bool:
        """Retorna True se o conteúdo é binário (imagem, áudio, vídeo)."""
        return self.type in (ContentType.IMAGE, ContentType.AUDIO, ContentType.VIDEO, ContentType.BASE64)

    model_config = {"arbitrary_types_allowed": True}


class Message(BaseModel):
    """Mensagem universal do OmniaChain.

    Suporta múltiplos conteúdos multi-modais em uma única mensagem.

    Exemplo::

        # Mensagem simples de texto
        msg = Message.user("Olá, como vai?")

        # Mensagem multi-modal
        msg = Message.user(
            MessageContent.text("Analise esta imagem:"),
            MessageContent.image("foto.png"),
        )
    """

    role: Role
    content: list[MessageContent]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def user(cls, *contents: Union[str, MessageContent]) -> Message:
        """Cria uma mensagem do usuário.

        Args:
            *contents: Strings são convertidas para TextContent automaticamente.

        Exemplo::

            msg = Message.user("Qual é a capital do Brasil?")
            msg = Message.user("Veja:", MessageContent.image("mapa.png"))
        """
        parsed = [
            MessageContent.text(c) if isinstance(c, str) else c
            for c in contents
        ]
        return cls(role=Role.USER, content=parsed)

    @classmethod
    def assistant(cls, *contents: Union[str, MessageContent]) -> Message:
        """Cria uma mensagem do assistente."""
        parsed = [
            MessageContent.text(c) if isinstance(c, str) else c
            for c in contents
        ]
        return cls(role=Role.ASSISTANT, content=parsed)

    @classmethod
    def system(cls, text: str) -> Message:
        """Cria uma mensagem de sistema.

        Exemplo::

            msg = Message.system("Você é um assistente útil.")
        """
        return cls(role=Role.SYSTEM, content=[MessageContent.text(text)])

    @classmethod
    def tool(cls, tool_name: str, result: Any, tool_call_id: Optional[str] = None) -> Message:
        """Cria uma mensagem de resultado de tool.

        Args:
            tool_name: Nome da tool que gerou o resultado.
            result: Resultado da execução.
            tool_call_id: ID da chamada de tool (para correlação).
        """
        content = MessageContent.text(str(result))
        content.metadata["tool_name"] = tool_name
        if tool_call_id:
            content.metadata["tool_call_id"] = tool_call_id
        return cls(role=Role.TOOL, content=[content])

    @property
    def text(self) -> str:
        """Extrai todo o conteúdo de texto da mensagem como string."""
        parts = []
        for c in self.content:
            if c.type == ContentType.TEXT:
                parts.append(str(c.data))
        return "\n".join(parts)

    @property
    def has_binary(self) -> bool:
        """Retorna True se a mensagem contém conteúdo binário."""
        return any(c.is_binary() for c in self.content)

    def __str__(self) -> str:
        return f"[{self.role.value}] {self.text[:100]}{'...' if len(self.text) > 100 else ''}"

    model_config = {"arbitrary_types_allowed": True}
