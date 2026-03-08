"""
OmniaChain — MCP Client: conecta agentes a servidores MCP.

Exemplo::

    client = MCPClient("http://localhost:8000")
    tools = await client.list_tools()
    result = await client.call_tool("memory_search", query="IA generativa")
"""

from __future__ import annotations

import json
from typing import Any, Optional


class MCPClient:
    """Cliente MCP para conectar a servidores MCP externos.

    Exemplo::

        async with MCPClient("http://localhost:8000") as client:
            tools = await client.list_tools()
            result = await client.call_tool("buscar", query="test")
    """

    def __init__(self, url: str = "", transport: str = "http") -> None:
        self.url = url
        self.transport = transport
        self._request_id = 0

    async def __aenter__(self) -> MCPClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _send_request(self, method: str, params: Optional[dict] = None) -> Any:
        """Envia uma requisição JSON-RPC ao servidor MCP."""
        import httpx

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.url, json=request)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise Exception(f"MCP Error: {data['error']}")
            return data.get("result")

    async def list_tools(self) -> list[dict[str, Any]]:
        """Lista todas as tools disponíveis no servidor."""
        result = await self._send_request("tools/list")
        return result.get("tools", []) if result else []

    async def call_tool(self, name: str, **kwargs: Any) -> Any:
        """Chama uma tool no servidor MCP.

        Args:
            name: Nome da tool.
            **kwargs: Argumentos para a tool.
        """
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": kwargs,
        })
        return result

    async def list_resources(self) -> list[dict[str, Any]]:
        """Lista recursos disponíveis no servidor."""
        result = await self._send_request("resources/list")
        return result.get("resources", []) if result else []

    async def read_resource(self, uri: str) -> Any:
        """Lê um recurso do servidor."""
        return await self._send_request("resources/read", {"uri": uri})

    async def list_prompts(self) -> list[dict[str, Any]]:
        """Lista prompts disponíveis no servidor."""
        result = await self._send_request("prompts/list")
        return result.get("prompts", []) if result else []

    async def get_prompt(self, name: str, **kwargs: Any) -> str:
        """Obtém um prompt do servidor."""
        result = await self._send_request("prompts/get", {"name": name, "arguments": kwargs})
        return result.get("content", "") if result else ""
