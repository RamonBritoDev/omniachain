"""OmniaChain — Loader de imagens (.jpg, .png, .webp, .gif)."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import MessageContent
from omniachain.loaders.base import BaseLoader

MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp",
    ".gif": "image/gif", ".bmp": "image/bmp",
    ".svg": "image/svg+xml", ".ico": "image/x-icon",
}


class ImageLoader(BaseLoader):
    """Carrega imagens e as prepara para envio a modelos com visão.

    Exemplo::

        loader = ImageLoader()
        content = await loader.load("foto.png")
    """

    SUPPORTED_EXTENSIONS = set(MIME_MAP.keys())

    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Carrega imagem e retorna MessageContent com dados base64."""
        try:
            if isinstance(source, bytes):
                data = source
                mime_type = "image/png"
                metadata: dict = {}
            else:
                path = Path(str(source))
                data = await self._read_file(path)
                ext = path.suffix.lower()
                mime_type = MIME_MAP.get(ext, "image/png")
                metadata = self._get_metadata(path)

            # Obter dimensões se PIL disponível
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(data))
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format or "unknown"
                metadata["mode"] = img.mode
            except ImportError:
                pass

            b64_data = base64.b64encode(data).decode("ascii")
            metadata["size_bytes"] = len(data)

            return MessageContent.image(b64_data, mime_type=mime_type, **metadata)

        except LoaderError:
            raise
        except FileNotFoundError as e:
            raise LoaderError(
                f"Imagem não encontrada: {source}",
                loader="ImageLoader",
                source=str(source),
                original_error=e,
            )
        except Exception as e:
            raise LoaderError(
                f"Erro ao carregar imagem: {e}",
                loader="ImageLoader",
                source=str(source),
                original_error=e,
            )
