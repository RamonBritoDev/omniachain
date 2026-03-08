"""OmniaChain — Tool de busca na web via DuckDuckGo."""

from omniachain.tools.base import tool


@tool(retries=3, timeout=15.0)
async def web_search(query: str, max_results: int = 5) -> str:
    """Busca informações na web usando DuckDuckGo.

    Args:
        query: Termo de busca.
        max_results: Número máximo de resultados (padrão: 5).

    Returns:
        Resultados da busca formatados com título, URL e resumo.
    """
    import httpx

    # DuckDuckGo HTML search
    async with httpx.AsyncClient(
        timeout=12.0,
        headers={"User-Agent": "OmniaChain/0.1 (Python)"},
        follow_redirects=True,
    ) as client:
        response = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
        )
        response.raise_for_status()

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")
        results_elements = soup.find_all("div", class_="result", limit=max_results)

        results = []
        for i, el in enumerate(results_elements, 1):
            title_el = el.find("a", class_="result__a")
            snippet_el = el.find("a", class_="result__snippet")

            title = title_el.get_text(strip=True) if title_el else "Sem título"
            url = title_el.get("href", "") if title_el else ""
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            results.append(f"{i}. {title}\n   URL: {url}\n   {snippet}")

        if not results:
            return f"Nenhum resultado encontrado para: {query}"

        return f"Resultados para '{query}':\n\n" + "\n\n".join(results)

    except ImportError:
        # Fallback sem BeautifulSoup
        import re

        text = re.sub(r"<[^>]+>", " ", response.text)
        text = re.sub(r"\s+", " ", text)[:3000]
        return f"Resultados (raw) para '{query}':\n{text}"
