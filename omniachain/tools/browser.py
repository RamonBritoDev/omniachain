"""OmniaChain — Tool de automação de browser via Playwright."""

from omniachain.tools.base import tool


@tool(timeout=30.0, retries=1)
async def browser_navigate(url: str, action: str = "read") -> str:
    """Navega a uma URL e extrai conteúdo ou faz screenshot.

    Requer Playwright instalado (pip install playwright && playwright install).

    Args:
        url: URL para navegar.
        action: Ação: "read" (extrai texto), "screenshot" (captura tela).

    Returns:
        Conteúdo da página ou caminho do screenshot.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "Erro: Playwright não instalado. Instale com: pip install playwright && playwright install chromium"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")

            if action == "screenshot":
                import tempfile
                import os

                path = os.path.join(tempfile.gettempdir(), "omniachain_screenshot.png")
                await page.screenshot(path=path, full_page=True)
                return f"Screenshot salvo em: {path}"
            else:
                # Extrair texto visível
                text = await page.inner_text("body")
                title = await page.title()
                return f"Título: {title}\nURL: {url}\n\nConteúdo:\n{text[:10000]}"

        finally:
            await browser.close()
