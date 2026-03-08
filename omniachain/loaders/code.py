"""OmniaChain — Loader de código fonte com metadados."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import MessageContent
from omniachain.loaders.base import BaseLoader

LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx", ".java": "java",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".cs": "csharp", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php", ".swift": "swift",
    ".kt": "kotlin", ".scala": "scala", ".r": "r",
    ".sql": "sql", ".sh": "bash", ".ps1": "powershell",
    ".html": "html", ".css": "css", ".scss": "scss",
    ".vue": "vue", ".svelte": "svelte",
}


class CodeLoader(BaseLoader):
    """Carrega código fonte com metadados de linguagem e estrutura.

    Exemplo::

        loader = CodeLoader()
        content = await loader.load("main.py")
        print(content.metadata["language"])  # "python"
    """

    SUPPORTED_EXTENSIONS = set(LANGUAGE_MAP.keys())

    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Carrega código fonte com metadados."""
        try:
            if isinstance(source, bytes):
                code = source.decode("utf-8")
                language = "unknown"
                metadata: dict = {}
            else:
                path = Path(str(source))
                code = await self._read_text_file(path)
                language = LANGUAGE_MAP.get(path.suffix.lower(), "unknown")
                metadata = self._get_metadata(path)

            lines = code.split("\n")
            metadata.update({
                "language": language,
                "line_count": len(lines),
                "char_count": len(code),
                "has_imports": any(
                    line.strip().startswith(("import ", "from ", "require(", "#include", "using "))
                    for line in lines[:50]
                ),
            })

            content = MessageContent.code(code, language=language)
            content.metadata.update(metadata)
            return content

        except Exception as e:
            raise LoaderError(
                f"Erro ao carregar código: {e}",
                loader="CodeLoader",
                source=str(source),
                original_error=e,
            )
