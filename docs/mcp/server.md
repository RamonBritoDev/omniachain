# MCP Server

Crie servidores MCP com decorators simples.

## Servidor Básico

```python
from omniachain import MCPServer

server = MCPServer("meu-servidor", version="1.0.0")

@server.tool
async def consultar_banco(query: str) -> str:
    """Consulta dados no banco."""
    return f"Resultado: {query}"

@server.tool
async def gerar_relatorio(tema: str, formato: str = "markdown") -> str:
    """Gera um relatório."""
    return f"# {tema}\n\nConteúdo..."

@server.resource("docs/{path}")
async def get_doc(path: str) -> str:
    """Retorna conteúdo de um documento."""
    return f"Documento: {path}"

@server.prompt
async def analise_prompt(tema: str) -> str:
    """Template de prompt para análise."""
    return f"Analise '{tema}' considerando aspectos técnicos e práticos."

# Rodar
await server.run(transport="stdio")  # ou transport="http"
```

## Transports

=== "stdio (Claude Desktop)"

    ```python
    await server.run(transport="stdio")
    ```

    Para usar com Claude Desktop, configure `claude_desktop_config.json`:
    ```json
    {
        "mcpServers": {
            "meu-servidor": {
                "command": "python",
                "args": ["meu_server.py"]
            }
        }
    }
    ```

=== "HTTP (rede)"

    ```python
    await server.run(transport="http", host="0.0.0.0", port=8080)
    ```

## MCP Memory Server

Servidor MCP pronto para memória vetorial:

```python
from omniachain.memory.mcp_memory import MCPMemoryServer

server = MCPMemoryServer(dsn="postgresql://localhost/omniachain")
await server.run(transport="stdio")
```
