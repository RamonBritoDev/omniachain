"""OmniaChain — Loader de PDF com extração de texto e imagens."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import ContentType, MessageContent
from omniachain.loaders.base import BaseLoader


class PDFLoader(BaseLoader):
    """Carrega PDFs extraindo texto e metadados.

    Exemplo::

        loader = PDFLoader()
        content = await loader.load("relatorio.pdf")
        print(content.data)  # Texto completo do PDF
    """

    SUPPORTED_EXTENSIONS = {".pdf"}

    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Carrega PDF e extrai texto."""
        try:
            from pypdf import PdfReader
            import io

            if isinstance(source, bytes):
                reader = PdfReader(io.BytesIO(source))
            else:
                reader = PdfReader(str(source))

            pages_text: list[str] = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"--- Página {i + 1} ---\n{text}")

            full_text = "\n\n".join(pages_text)

            metadata = self._get_metadata(source) if not isinstance(source, bytes) else {}
            metadata.update({
                "page_count": len(reader.pages),
                "char_count": len(full_text),
                "pdf_info": {k: str(v) for k, v in (reader.metadata or {}).items()} if reader.metadata else {},
            })

            content = MessageContent(
                type=ContentType.DOCUMENT,
                data=full_text,
                mime_type="application/pdf",
                metadata=metadata,
            )
            return content

        except ImportError:
            raise LoaderError(
                "Pacote 'pypdf' não instalado.",
                loader="PDFLoader",
                source=str(source),
                suggestion="Instale com: pip install pypdf",
            )
        except Exception as e:
            raise LoaderError(
                f"Erro ao carregar PDF: {e}",
                loader="PDFLoader",
                source=str(source),
                original_error=e,
            )
