"""OmniaChain — Loader de arquivos de texto (.txt, .md, .rst)."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import MessageContent
from omniachain.loaders.base import BaseLoader


class TextLoader(BaseLoader):
    """Carrega arquivos de texto plano.

    Suporta .txt, .md, .rst, .log, .ini, .cfg, .yaml, .yml, .json, .xml, .toml.

    Exemplo::

        loader = TextLoader()
        content = await loader.load("README.md")
        print(content.data)  # Conteúdo do arquivo
    """

    SUPPORTED_EXTENSIONS = {
        ".txt", ".md", ".rst", ".log", ".ini", ".cfg",
        ".yaml", ".yml", ".json", ".xml", ".toml", ".env",
    }

    def __init__(self, encoding: str = "utf-8") -> None:
        self.encoding = encoding

    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Carrega arquivo de texto e retorna MessageContent."""
        try:
            if isinstance(source, bytes):
                text = source.decode(self.encoding)
            else:
                text = await self._read_text_file(source, self.encoding)

            metadata = self._get_metadata(source) if not isinstance(source, bytes) else {}
            metadata["encoding"] = self.encoding
            metadata["char_count"] = len(text)
            metadata["line_count"] = text.count("\n") + 1

            content = MessageContent.text(text)
            content.metadata.update(metadata)
            return content

        except UnicodeDecodeError as e:
            raise LoaderError(
                f"Erro de encoding ao ler arquivo: {e}",
                loader="TextLoader",
                source=str(source),
                suggestion=f"Tente outro encoding. Atual: {self.encoding}",
                original_error=e,
            )
        except FileNotFoundError as e:
            raise LoaderError(
                f"Arquivo não encontrado: {source}",
                loader="TextLoader",
                source=str(source),
                original_error=e,
            )
        except Exception as e:
            raise LoaderError(
                f"Erro ao carregar texto: {e}",
                loader="TextLoader",
                source=str(source),
                original_error=e,
            )
