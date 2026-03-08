"""
OmniaChain — AutoLoader: detecta tipo de input e carrega automaticamente.

Exemplo::

    contents = await AutoLoader.load(["relatorio.pdf", "foto.png", "dados.csv"])
    # Retorna [MessageContent(DOCUMENT), MessageContent(IMAGE), MessageContent(TABLE)]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Type, Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import MessageContent
from omniachain.loaders.base import BaseLoader
from omniachain.loaders.text import TextLoader
from omniachain.loaders.pdf import PDFLoader
from omniachain.loaders.image import ImageLoader
from omniachain.loaders.audio import AudioLoader
from omniachain.loaders.video import VideoLoader
from omniachain.loaders.csv import CSVLoader
from omniachain.loaders.code import CodeLoader
from omniachain.loaders.url import URLLoader
from omniachain.loaders.base64 import Base64Loader


# Mapeamento extensão → Loader
EXTENSION_MAP: dict[str, Type[BaseLoader]] = {}
for _loader_cls in [TextLoader, PDFLoader, ImageLoader, AudioLoader, VideoLoader, CSVLoader, CodeLoader]:
    for _ext in _loader_cls.SUPPORTED_EXTENSIONS:
        EXTENSION_MAP[_ext] = _loader_cls


class AutoLoader:
    """Detecta o tipo de input automaticamente e usa o loader correto.

    Suporta: texto, PDF, imagem, áudio, vídeo, CSV/Excel, código, URL e base64.

    Exemplo::

        # Carrega múltiplos inputs de tipo diferente
        contents = await AutoLoader.load([
            "relatorio.pdf",
            "foto.png",
            "dados.csv",
            "https://example.com",
            "main.py",
        ])

        # Carrega um único input
        content = await AutoLoader.load_single("foto.png")
    """

    @classmethod
    async def load(cls, inputs: list[Union[str, Path, bytes]]) -> list[MessageContent]:
        """Carrega múltiplos inputs detectando tipo automaticamente.

        Args:
            inputs: Lista de caminhos de arquivo, URLs, ou bytes.

        Returns:
            Lista de MessageContent prontos para uso.
        """
        import asyncio

        tasks = [cls.load_single(inp) for inp in inputs]
        return await asyncio.gather(*tasks)

    @classmethod
    async def load_single(cls, source: Union[str, Path, bytes]) -> MessageContent:
        """Carrega um único input detectando tipo automaticamente.

        A detecção segue esta ordem:
        1. Se URL → URLLoader
        2. Se YouTube URL → VideoLoader
        3. Se Path com extensão conhecida → loader específico
        4. Se bytes → Base64Loader (detecta via magic bytes)
        5. Fallback → TextLoader
        """
        try:
            loader_cls = cls._detect_loader(source)
            loader = loader_cls()
            return await loader.load(source)
        except LoaderError:
            raise
        except Exception as e:
            raise LoaderError(
                f"Erro ao auto-detectar e carregar: {e}",
                loader="AutoLoader",
                source=str(source)[:100],
                suggestion="Verifique o tipo do arquivo ou passe o loader correto manualmente.",
                original_error=e,
            )

    @classmethod
    def _detect_loader(cls, source: Union[str, Path, bytes]) -> Type[BaseLoader]:
        """Detecta o loader correto para o source dado."""
        # 1. Bytes → Base64Loader
        if isinstance(source, bytes):
            return Base64Loader

        source_str = str(source)

        # 2. YouTube URL → VideoLoader
        if VideoLoader.is_youtube_url(source_str):
            return VideoLoader

        # 3. URL genérica → URLLoader
        if source_str.startswith(("http://", "https://")):
            return URLLoader

        # 4. Path com extensão → lookup no mapa
        ext = Path(source_str).suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

        # 5. Fallback → TextLoader
        return TextLoader

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """Retorna todas as extensões suportadas."""
        return sorted(EXTENSION_MAP.keys())
