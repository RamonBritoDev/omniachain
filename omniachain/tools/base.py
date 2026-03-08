"""
OmniaChain — @tool decorator com validação automática.

Transforma qualquer função async em uma tool utilizável por agentes.
Gera JSON schema automaticamente a partir de type hints e docstrings.

Exemplo::

    @tool
    async def buscar_preco(produto: str, moeda: str = "BRL") -> float:
        \"\"\"Busca o preço atual de um produto no mercado.\"\"\"
        return 42.0

    # O schema JSON é gerado automaticamente:
    print(buscar_preco.schema)
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import json
import time
from typing import Any, Callable, Coroutine, Optional, get_type_hints

from pydantic import BaseModel, Field

from omniachain.core.errors import ToolError


# Type mapping Python → JSON Schema
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


class ToolResult(BaseModel):
    """Resultado de execução de uma tool."""
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    tool_name: str = ""
    cached: bool = False


class Tool:
    """Wrapper que encapsula uma função como tool para LLMs.

    Attributes:
        func: Função original.
        name: Nome da tool.
        description: Descrição para o LLM.
        schema: JSON schema dos parâmetros.
        retries: Número de tentativas.
        timeout: Timeout em segundos.
    """

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        retries: int = 3,
        timeout: float = 30.0,
        cache: bool = False,
    ) -> None:
        self.func = func
        self.name = name or func.__name__
        self.description = description or (func.__doc__ or "").strip().split("\n")[0]
        self.retries = retries
        self.timeout = timeout
        self.cache = cache
        self._cache: dict[str, Any] = {}

        # Gerar schema
        self.schema = self._generate_schema()

        # Preservar metadata da função original
        functools.update_wrapper(self, func)

    def _generate_schema(self) -> dict[str, Any]:
        """Gera JSON schema a partir das type hints da função."""
        sig = inspect.signature(self.func)
        hints = get_type_hints(self.func)

        # Remover 'return' das hints
        hints.pop("return", None)

        properties: dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls", "_agent_fingerprint", "_agent_name"):
                continue

            hint = hints.get(param_name, str)
            json_type = _TYPE_MAP.get(hint, "string")

            prop: dict[str, Any] = {"type": json_type}

            # Extrair descrição do docstring se possível
            doc = self.func.__doc__ or ""
            for line in doc.split("\n"):
                line = line.strip()
                if line.startswith(f"{param_name}:") or line.startswith(f"{param_name} "):
                    prop["description"] = line.split(":", 1)[-1].strip() if ":" in line else line

            if param.default is inspect.Parameter.empty:
                required.append(param_name)
            else:
                prop["default"] = param.default

            properties[param_name] = prop

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_openai_schema(self) -> dict[str, Any]:
        """Retorna schema no formato OpenAI/tool calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema,
            },
        }

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Retorna schema no formato Anthropic."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.schema,
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Executa a tool com retry, timeout e cache.

        Args:
            **kwargs: Argumentos para a função.

        Returns:
            ToolResult com resultado ou erro.
        """
        # Cache check
        if self.cache:
            cache_key = json.dumps(kwargs, sort_keys=True, default=str)
            if cache_key in self._cache:
                return ToolResult(
                    success=True,
                    result=self._cache[cache_key],
                    tool_name=self.name,
                    cached=True,
                )

        last_error: Optional[Exception] = None

        for attempt in range(1, self.retries + 1):
            start = time.perf_counter()
            try:
                if asyncio.iscoroutinefunction(self.func):
                    result = await asyncio.wait_for(
                        self.func(**kwargs),
                        timeout=self.timeout,
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self.func, **kwargs),
                        timeout=self.timeout,
                    )

                latency = (time.perf_counter() - start) * 1000

                # Cache store
                if self.cache:
                    cache_key = json.dumps(kwargs, sort_keys=True, default=str)
                    self._cache[cache_key] = result

                return ToolResult(
                    success=True,
                    result=result,
                    latency_ms=latency,
                    tool_name=self.name,
                )

            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError(
                    f"Tool '{self.name}' excedeu timeout de {self.timeout}s"
                )
            except Exception as e:
                last_error = e

        latency = (time.perf_counter() - start) * 1000
        return ToolResult(
            success=False,
            error=f"Tool '{self.name}' falhou após {self.retries} tentativa(s): {last_error}",
            latency_ms=latency,
            tool_name=self.name,
        )

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Permite chamar a tool diretamente como função."""
        result = await self.execute(**kwargs)
        if not result.success:
            raise ToolError(
                result.error or f"Tool '{self.name}' falhou.",
                tool_name=self.name,
            )
        return result.result

    def __repr__(self) -> str:
        return f"Tool(name={self.name!r})"


def tool(
    func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    retries: int = 3,
    timeout: float = 30.0,
    cache: bool = False,
) -> Any:
    """Decorator que transforma uma função em uma Tool.

    Pode ser usado com ou sem parênteses:

    Exemplo::

        @tool
        async def minha_tool(query: str) -> str:
            \"\"\"Descrição da tool.\"\"\"
            return f"Resultado: {query}"

        @tool(retries=5, cache=True)
        async def outra_tool(x: int) -> int:
            \"\"\"Outra tool com retry e cache.\"\"\"
            return x * 2
    """

    def decorator(f: Callable) -> Tool:
        return Tool(
            func=f,
            name=name,
            description=description,
            retries=retries,
            timeout=timeout,
            cache=cache,
        )

    if func is not None:
        return decorator(func)
    return decorator
