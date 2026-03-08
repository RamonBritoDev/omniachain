"""Exemplo 04 — Servidor MCP com memória vetorial."""

import asyncio
from omniachain import MCPServer
from omniachain.memory.mcp_memory import MCPMemoryServer


# Opção 1: MCP Memory Server dedicado
async def run_memory_server():
    """Inicia servidor MCP de memória vetorial."""
    server = MCPMemoryServer(
        dsn="postgresql://user:pass@localhost/omniachain",
        name="memory-server",
    )
    await server.run(transport="stdio")


# Opção 2: MCP Server customizado com tools
async def run_custom_server():
    """Cria um servidor MCP customizado."""
    server = MCPServer("meu-servidor", version="1.0.0")

    @server.tool
    async def consultar_banco(query: str) -> str:
        """Consulta dados no banco de dados."""
        return f"Resultado para: {query}"

    @server.tool
    async def gerar_relatorio(tema: str, formato: str = "markdown") -> str:
        """Gera um relatório sobre o tema especificado."""
        return f"# Relatório: {tema}\n\nConteúdo gerado..."

    @server.resource("docs/{path}")
    async def get_doc(path: str) -> str:
        """Retorna o conteúdo de um documento."""
        return f"Conteúdo do documento: {path}"

    @server.prompt
    async def analise_prompt(tema: str) -> str:
        """Template de prompt para análise."""
        return f"Analise detalhadamente o tema '{tema}'..."

    await server.run(transport="stdio")


if __name__ == "__main__":
    asyncio.run(run_custom_server())
