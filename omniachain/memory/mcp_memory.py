"""
OmniaChain — MCP Memory Server: expõe memória vetorial via MCP.

Permite que qualquer agente (interno ou externo) acesse memória vetorial via protocolo MCP.

Exemplo::

    from omniachain.memory.mcp_memory import MCPMemoryServer

    server = MCPMemoryServer(dsn="postgresql://localhost/omniachain")
    await server.run(transport="stdio")
"""

from __future__ import annotations

from typing import Any, Optional

from omniachain.memory.vector import VectorMemory


class MCPMemoryServer:
    """Servidor MCP dedicado para memória vetorial.

    Expõe 3 tools via MCP:
    - memory_store: Armazena conteúdo com embedding
    - memory_search: Busca semântica
    - memory_delete: Remove por ID

    Exemplo::

        server = MCPMemoryServer(dsn="postgresql://localhost/db")
        await server.run(transport="stdio")
    """

    def __init__(
        self,
        dsn: Optional[str] = None,
        name: str = "omniachain-memory",
        embedding_provider: Optional[Any] = None,
    ) -> None:
        self.name = name
        self.memory = VectorMemory(dsn=dsn, embedding_provider=embedding_provider)
        self._server: Optional[Any] = None

    async def initialize(self) -> None:
        """Inicializa memória vetorial e servidor MCP."""
        await self.memory.initialize()

    async def memory_store(self, content: str, metadata: str = "{}") -> str:
        """Armazena conteúdo com embedding vetorial.

        Args:
            content: Texto para armazenar.
            metadata: Metadados em JSON.

        Returns:
            ID do documento armazenado.
        """
        import json
        meta = json.loads(metadata) if metadata else {}
        doc_id = await self.memory.store(content, metadata=meta)
        return f"Armazenado com sucesso. ID: {doc_id}"

    async def memory_search(self, query: str, limit: int = 5) -> str:
        """Busca semântica por similaridade.

        Args:
            query: Texto de busca.
            limit: Número máximo de resultados.

        Returns:
            Resultados formatados com score de similaridade.
        """
        import json
        results = await self.memory.search(query, limit=limit)

        if not results:
            return "Nenhum resultado encontrado."

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. [Score: {r['score']:.4f}] {r['content'][:200]}"
            )

        return "\n".join(formatted)

    async def memory_delete(self, doc_id: str) -> str:
        """Remove documento por ID.

        Args:
            doc_id: ID do documento a remover.

        Returns:
            Confirmação da remoção.
        """
        success = await self.memory.delete(doc_id)
        if success:
            return f"Documento {doc_id} removido com sucesso."
        return f"Documento {doc_id} não encontrado."

    async def run(self, transport: str = "stdio", port: int = 8001) -> None:
        """Inicia o servidor MCP.

        Args:
            transport: Tipo de transporte ("stdio" ou "http").
            port: Porta para transporte HTTP.
        """
        await self.initialize()

        # Late import to avoid circular deps
        from omniachain.mcp.server import MCPServer

        server = MCPServer(self.name)

        # Registrar tools
        server.register_tool(
            self.memory_store,
            name="memory_store",
            description="Armazena conteúdo com embedding vetorial para busca semântica posterior.",
        )
        server.register_tool(
            self.memory_search,
            name="memory_search",
            description="Busca semântica por similaridade em memórias armazenadas.",
        )
        server.register_tool(
            self.memory_delete,
            name="memory_delete",
            description="Remove um documento da memória por ID.",
        )

        await server.run(transport=transport, port=port)

    async def close(self) -> None:
        """Fecha conexões."""
        await self.memory.close()
