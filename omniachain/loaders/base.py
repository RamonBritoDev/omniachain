"""
OmniaChain — Interface base para loaders de conteúdo.

Todos os loaders (PDF, imagem, áudio, etc.) herdam desta classe base.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any, Union

from omniachain.core.message import MessageContent


class BaseLoader(abc.ABC):
    """Interface base que todos os loaders devem implementar.

    Cada loader converte um tipo específico de input em ``MessageContent``
    pronto para uso em mensagens.

    Exemplo de implementação::

        class MeuLoader(BaseLoader):
            SUPPORTED_EXTENSIONS = {".xyz"}

            async def load(self, source):
                data = await self._read_file(source)
                return MessageContent.text(data.decode())
    """

    SUPPORTED_EXTENSIONS: set[str] = set()

    @abc.abstractmethod
    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Carrega o source e retorna MessageContent.

        Args:
            source: Caminho do arquivo, URL, ou bytes raw.

        Returns:
            MessageContent pronto para inclusão em uma Message.
        """
        ...

    @classmethod
    def supports(cls, source: Union[str, Path]) -> bool:
        """Verifica se este loader suporta o source dado.

        Args:
            source: Caminho ou identificador do arquivo.
        """
        if isinstance(source, (str, Path)):
            ext = Path(str(source)).suffix.lower()
            return ext in cls.SUPPORTED_EXTENSIONS
        return False

    async def _read_file(self, path: Union[str, Path]) -> bytes:
        """Lê arquivo de forma assíncrona.

        Args:
            path: Caminho do arquivo.

        Returns:
            Conteúdo do arquivo em bytes.
        """
        import aiofiles

        async with aiofiles.open(str(path), "rb") as f:
            return await f.read()

    async def _read_text_file(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        """Lê arquivo de texto de forma assíncrona."""
        import aiofiles

        async with aiofiles.open(str(path), "r", encoding=encoding) as f:
            return await f.read()

    def _get_metadata(self, source: Union[str, Path]) -> dict[str, Any]:
        """Extrai metadados básicos de um arquivo."""
        path = Path(str(source))
        meta: dict[str, Any] = {"filename": path.name, "extension": path.suffix.lower()}
        if path.exists():
            stat = path.stat()
            meta["size_bytes"] = stat.st_size
            meta["modified"] = stat.st_mtime
        return meta
