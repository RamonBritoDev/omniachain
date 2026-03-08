"""
OmniaChain — Decorators MCP: @server.tool, @server.resource, @server.prompt.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Optional, get_type_hints

_TYPE_MAP = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


class MCPToolDef:
    """Definição de uma MCP tool."""
    def __init__(self, func: Callable, name: str, description: str, schema: dict) -> None:
        self.func = func
        self.name = name
        self.description = description
        self.schema = schema
        functools.update_wrapper(self, func)

    async def __call__(self, **kwargs: Any) -> Any:
        if inspect.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        import asyncio
        return await asyncio.to_thread(self.func, **kwargs)


class MCPResourceDef:
    """Definição de um MCP resource."""
    def __init__(self, func: Callable, pattern: str, description: str) -> None:
        self.func = func
        self.pattern = pattern
        self.description = description
        functools.update_wrapper(self, func)


class MCPPromptDef:
    """Definição de um MCP prompt template."""
    def __init__(self, func: Callable, name: str, description: str) -> None:
        self.func = func
        self.name = name
        self.description = description
        functools.update_wrapper(self, func)


def _generate_schema(func: Callable) -> dict[str, Any]:
    """Gera JSON schema a partir da assinatura da função."""
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    hints.pop("return", None)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        hint = hints.get(name, str)
        json_type = _TYPE_MAP.get(hint, "string")
        properties[name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            properties[name]["default"] = param.default

    return {"type": "object", "properties": properties, "required": required}


def mcp_tool(func: Optional[Callable] = None, *, name: Optional[str] = None, description: Optional[str] = None) -> Any:
    """Decorator para registrar uma função como MCP tool."""
    def decorator(f: Callable) -> MCPToolDef:
        tool_name = name or f.__name__
        tool_desc = description or (f.__doc__ or "").strip().split("\n")[0]
        schema = _generate_schema(f)
        return MCPToolDef(func=f, name=tool_name, description=tool_desc, schema=schema)

    if func is not None:
        return decorator(func)
    return decorator


def mcp_resource(pattern: str, *, description: Optional[str] = None) -> Callable:
    """Decorator para registrar um handler de resource MCP."""
    def decorator(f: Callable) -> MCPResourceDef:
        desc = description or (f.__doc__ or "").strip().split("\n")[0]
        return MCPResourceDef(func=f, pattern=pattern, description=desc)
    return decorator


def mcp_prompt(func: Optional[Callable] = None, *, name: Optional[str] = None, description: Optional[str] = None) -> Any:
    """Decorator para registrar um prompt template MCP."""
    def decorator(f: Callable) -> MCPPromptDef:
        prompt_name = name or f.__name__
        prompt_desc = description or (f.__doc__ or "").strip().split("\n")[0]
        return MCPPromptDef(func=f, name=prompt_name, description=prompt_desc)

    if func is not None:
        return decorator(func)
    return decorator
