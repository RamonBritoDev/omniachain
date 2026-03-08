"""OmniaChain — Loader de dados base64."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import MessageContent
from omniachain.loaders.base import BaseLoader

# Magic bytes para detecção de tipo
MAGIC_BYTES = {
    b"\x89PNG": ("image/png", "image"),
    b"\xff\xd8\xff": ("image/jpeg", "image"),
    b"GIF8": ("image/gif", "image"),
    b"RIFF": ("audio/wav", "audio"),
    b"\xff\xfb": ("audio/mp3", "audio"),
    b"\x00\x00\x00": ("video/mp4", "video"),
    b"%PDF": ("application/pdf", "document"),
    b"PK": ("application/zip", "document"),
}


class Base64Loader(BaseLoader):
    """Carrega dados raw em base64, detectando tipo automaticamente.

    Exemplo::

        loader = Base64Loader()
        content = await loader.load(b64_string)
    """

    SUPPORTED_EXTENSIONS: set[str] = set()

    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Decodifica base64 e detecta tipo automaticamente."""
        try:
            if isinstance(source, bytes):
                raw_data = source
            elif isinstance(source, str):
                # Remove prefixo data URI se presente
                if source.startswith("data:"):
                    parts = source.split(",", 1)
                    source = parts[1] if len(parts) > 1 else source
                raw_data = base64.b64decode(source)
            else:
                raw_data = await self._read_file(source)

            mime_type, content_type = self._detect_type(raw_data)

            metadata = {
                "raw_size_bytes": len(raw_data),
                "detected_mime": mime_type,
                "detected_type": content_type,
            }

            b64 = base64.b64encode(raw_data).decode("ascii")
            return MessageContent.from_base64(b64, mime_type=mime_type, **metadata)

        except Exception as e:
            raise LoaderError(
                f"Erro ao processar dados base64: {e}",
                loader="Base64Loader",
                source="base64 data",
                original_error=e,
            )

    def _detect_type(self, data: bytes) -> tuple[str, str]:
        """Detecta MIME type a partir dos magic bytes."""
        for magic, (mime, ctype) in MAGIC_BYTES.items():
            if data[:len(magic)] == magic:
                return mime, ctype
        return "application/octet-stream", "base64"
