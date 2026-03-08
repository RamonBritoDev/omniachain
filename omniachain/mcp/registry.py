"""OmniaChain — MCP Registry: auto-discovery de servidores MCP."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class MCPServerInfo(BaseModel):
    """Info de um servidor MCP registrado."""
    name: str
    url: str = ""
    transport: str = "stdio"
    command: str = ""
    tools: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MCPRegistry:
    """Registry para auto-discovery de servidores MCP.

    Exemplo::

        registry = MCPRegistry()
        registry.register("meu-server", url="http://localhost:8000")
        servers = registry.discover("busca")
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerInfo] = {}

    def register(self, name: str, *, url: str = "", transport: str = "stdio", command: str = "", **kwargs: Any) -> None:
        """Registra um servidor MCP."""
        self._servers[name] = MCPServerInfo(name=name, url=url, transport=transport, command=command, **kwargs)

    def unregister(self, name: str) -> None:
        """Remove um servidor do registry."""
        self._servers.pop(name, None)

    def get(self, name: str) -> Optional[MCPServerInfo]:
        """Obtém info de um servidor por nome."""
        return self._servers.get(name)

    def list_servers(self) -> list[MCPServerInfo]:
        """Lista todos os servidores registrados."""
        return list(self._servers.values())

    def discover(self, capability: str) -> list[MCPServerInfo]:
        """Descobre servidores que possuem uma capability (tool ou resource)."""
        results = []
        for server in self._servers.values():
            if capability in server.tools or capability in server.resources:
                results.append(server)
        return results

    def find_tool(self, tool_name: str) -> Optional[MCPServerInfo]:
        """Encontra o servidor que fornece uma tool específica."""
        for server in self._servers.values():
            if tool_name in server.tools:
                return server
        return None
