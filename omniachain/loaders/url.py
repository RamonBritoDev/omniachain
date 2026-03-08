"""OmniaChain — Loader de URL com scraping inteligente."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import MessageContent
from omniachain.loaders.base import BaseLoader


class URLLoader(BaseLoader):
    """Faz scraping inteligente de URLs e retorna conteúdo limpo.

    Exemplo::

        loader = URLLoader()
        content = await loader.load("https://example.com")
        print(content.data)  # Texto limpo da página
    """

    SUPPORTED_EXTENSIONS: set[str] = set()  # URLs não têm extensão fixa

    @classmethod
    def supports(cls, source: Union[str, Path]) -> bool:
        """Verifica se a source é uma URL."""
        s = str(source)
        return s.startswith(("http://", "https://"))

    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Faz scraping da URL e retorna texto limpo."""
        url = str(source)

        try:
            import httpx

            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "OmniaChain/0.1 (Python)"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text

            # Extrair texto limpo do HTML
            text = self._extract_text(html_content)
            title = self._extract_title(html_content)

            metadata = {
                "url": url,
                "title": title,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "char_count": len(text),
            }

            content = MessageContent.text(f"Título: {title}\nURL: {url}\n\n{text}")
            content.metadata.update(metadata)
            return content

        except ImportError:
            raise LoaderError(
                "Pacote 'httpx' não instalado.",
                loader="URLLoader",
                source=url,
                suggestion="Instale com: pip install httpx",
            )
        except Exception as e:
            raise LoaderError(
                f"Erro ao fazer scraping de {url}: {e}",
                loader="URLLoader",
                source=url,
                suggestion="Verifique se a URL está acessível.",
                original_error=e,
            )

    def _extract_text(self, html: str) -> str:
        """Extrai texto limpo de HTML usando BeautifulSoup."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remover scripts, styles e nav
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Tentar encontrar conteúdo principal
            main = soup.find("main") or soup.find("article") or soup.find("body")
            if main:
                text = main.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Limpar linhas vazias excessivas
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            return "\n".join(lines)

        except ImportError:
            # Fallback: regex básico
            import re
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text)
            return text.strip()

    def _extract_title(self, html: str) -> str:
        """Extrai título da página."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            title_tag = soup.find("title")
            return title_tag.get_text(strip=True) if title_tag else "Sem título"
        except ImportError:
            import re
            match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else "Sem título"
