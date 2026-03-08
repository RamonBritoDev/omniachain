"""
OmniaChain — MCP Server: cria e expõe MCP Server completo.

Exemplo::

    server = MCPServer("meu-servidor")

    @server.tool
    async def consultar(id: str) -> dict:
        \"\"\"Consulta dados.\"\"\"
        return {"id": id}

    @server.resource("docs/{path}")
    async def get_doc(path: str) -> str:
        return f"Conteúdo de {path}"

    await server.run(transport="stdio")
"""

from __future__ import annotations

import inspect
import json
import re
from typing import Any, Callable, Literal, Optional, get_type_hints

from omniachain.mcp.decorators import MCPToolDef, MCPResourceDef, MCPPromptDef, _generate_schema


class MCPServer:
    """Servidor MCP completo com suporte a tools, resources e prompts.

    Exemplo::

        server = MCPServer("meu-server", version="1.0.0")

        @server.tool
        async def minha_tool(param: str) -> str:
            \"\"\"Descrição da tool.\"\"\"
            return f"Resultado: {param}"

        await server.run(transport="stdio")
    """

    def __init__(self, name: str, version: str = "1.0.0") -> None:
        self.name = name
        self.version = version
        self._tools: dict[str, MCPToolDef] = {}
        self._resources: dict[str, MCPResourceDef] = {}
        self._prompts: dict[str, MCPPromptDef] = {}

    def tool(self, func: Optional[Callable] = None, *, description: Optional[str] = None) -> Any:
        """Decorator para registrar uma MCP tool.

        Exemplo::

            @server.tool
            async def buscar(query: str) -> str:
                \"\"\"Busca informações.\"\"\"
                return "resultado"
        """
        def decorator(f: Callable) -> MCPToolDef:
            tool_name = f.__name__
            tool_desc = description or (f.__doc__ or "").strip().split("\n")[0]
            schema = _generate_schema(f)
            tool_def = MCPToolDef(func=f, name=tool_name, description=tool_desc, schema=schema)
            self._tools[tool_name] = tool_def
            return tool_def

        if func is not None:
            return decorator(func)
        return decorator

    def register_tool(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """Registra uma função como tool programaticamente (sem decorator)."""
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip().split("\n")[0]
        schema = _generate_schema(func)
        self._tools[tool_name] = MCPToolDef(func=func, name=tool_name, description=tool_desc, schema=schema)

    def resource(self, pattern: str) -> Callable:
        """Decorator para registrar um handler de resource.

        Exemplo::

            @server.resource("relatorios/{ano}/{mes}")
            async def get_relatorio(ano: str, mes: str) -> str:
                return f"Relatório {mes}/{ano}"
        """
        def decorator(f: Callable) -> MCPResourceDef:
            desc = (f.__doc__ or "").strip().split("\n")[0]
            resource_def = MCPResourceDef(func=f, pattern=pattern, description=desc)
            self._resources[pattern] = resource_def
            return resource_def
        return decorator

    def prompt(self, func: Optional[Callable] = None, *, description: Optional[str] = None) -> Any:
        """Decorator para registrar um prompt template.

        Exemplo::

            @server.prompt
            async def analise(tema: str) -> str:
                return f"Analise {tema} em detalhes..."
        """
        def decorator(f: Callable) -> MCPPromptDef:
            prompt_name = f.__name__
            prompt_desc = description or (f.__doc__ or "").strip().split("\n")[0]
            prompt_def = MCPPromptDef(func=f, name=prompt_name, description=prompt_desc)
            self._prompts[prompt_name] = prompt_def
            return prompt_def

        if func is not None:
            return decorator(func)
        return decorator

    async def _handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Processa uma requisição JSON-RPC."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True} if self._tools else {},
                        "resources": {"listChanged": True} if self._resources else {},
                        "prompts": {"listChanged": True} if self._prompts else {},
                    },
                    "serverInfo": {"name": self.name, "version": self.version},
                }
            elif method == "tools/list":
                result = {
                    "tools": [
                        {"name": t.name, "description": t.description, "inputSchema": t.schema}
                        for t in self._tools.values()
                    ]
                }
            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                if tool_name not in self._tools:
                    return self._error(req_id, -32602, f"Tool '{tool_name}' not found")
                tool_result = await self._tools[tool_name](**arguments)
                result = {"content": [{"type": "text", "text": str(tool_result)}]}
            elif method == "resources/list":
                result = {
                    "resources": [
                        {"uri": r.pattern, "name": r.pattern, "description": r.description}
                        for r in self._resources.values()
                    ]
                }
            elif method == "resources/read":
                uri = params.get("uri", "")
                content = await self._resolve_resource(uri)
                result = {"contents": [{"uri": uri, "mimeType": "text/plain", "text": content}]}
            elif method == "prompts/list":
                result = {
                    "prompts": [
                        {"name": p.name, "description": p.description}
                        for p in self._prompts.values()
                    ]
                }
            elif method == "prompts/get":
                prompt_name = params.get("name", "")
                if prompt_name not in self._prompts:
                    return self._error(req_id, -32602, f"Prompt '{prompt_name}' not found")
                arguments = params.get("arguments", {})
                prompt_result = await self._prompts[prompt_name].func(**arguments)
                result = {"messages": [{"role": "user", "content": {"type": "text", "text": prompt_result}}]}
            else:
                return self._error(req_id, -32601, f"Method '{method}' not found")

            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        except Exception as e:
            return self._error(req_id, -32603, str(e))

    async def _resolve_resource(self, uri: str) -> str:
        """Resolve uma URI de resource."""
        for pattern, resource in self._resources.items():
            regex = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern)
            match = re.match(f"^{regex}$", uri)
            if match:
                kwargs = match.groupdict()
                if inspect.iscoroutinefunction(resource.func):
                    return await resource.func(**kwargs)
                return resource.func(**kwargs)
        raise ValueError(f"Resource not found: {uri}")

    def _error(self, req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    async def run(self, transport: Literal["stdio", "http"] = "stdio", port: int = 8000) -> None:
        """Inicia o servidor MCP.

        Args:
            transport: "stdio" para stdin/stdout ou "http" para HTTP.
            port: Porta para transporte HTTP.
        """
        from omniachain.mcp.transport import StdioTransport, HTTPTransport

        if transport == "stdio":
            t = StdioTransport(handler=self._handle_request)
        else:
            t = HTTPTransport(handler=self._handle_request, port=port)

        await t.run()
