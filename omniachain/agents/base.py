"""
OmniaChain — Agente base com loop de raciocínio.

Exemplo::

    agent = Agent(provider=Anthropic(), tools=[web_search, calculator], memory="buffer")
    result = await agent.run("Qual é a raiz quadrada do PIB do Brasil?")
    print(result.content)
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Literal, Optional, Union

from omniachain.core.context import Context
from omniachain.core.errors import OmniaError
from omniachain.core.message import Message
from omniachain.core.response import Response, Usage
from omniachain.loaders.auto import AutoLoader
from omniachain.memory.buffer import BufferMemory
from omniachain.memory.summary import SummaryMemory
from omniachain.observability.logger import get_logger
from omniachain.providers.base import BaseProvider
from omniachain.security.keypair import KeyPair
from omniachain.security.permissions import Permissions
from omniachain.tools.base import Tool


logger = get_logger("agent")


class BaseAgent:
    """Agente base com loop de raciocínio e tool calling.

    Atributos configuráveis:
    - provider: Provider de IA
    - tools: Lista de Tools disponíveis
    - memory: Sistema de memória
    - system_prompt: Prompt de sistema
    - max_iterations: Máximo de iterações no loop de raciocínio
    """

    def __init__(
        self,
        provider: Union[BaseProvider, str, None] = None,
        tools: Optional[list[Tool]] = None,
        memory: Union[str, BufferMemory, SummaryMemory, None] = None,
        system_prompt: str = "Você é um assistente de IA útil e preciso.",
        name: str = "agent",
        max_iterations: int = 10,
        keypair: Optional[KeyPair] = None,
        permissions: Optional[Permissions] = None,
    ) -> None:
        self.provider_instance: Optional[BaseProvider] = provider if isinstance(provider, BaseProvider) else None
        self.provider: Any = provider
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.name = name
        self.max_iterations = max_iterations
        self.keypair = keypair
        self.permissions = permissions
        self._resolved_provider: Optional[BaseProvider] = self.provider_instance

        # Setup memory
        if isinstance(memory, str):
            if memory == "buffer":
                self.memory: Any = BufferMemory()
            elif memory == "summary":
                self.memory = SummaryMemory()
            else:
                self.memory = BufferMemory()
        else:
            self.memory = memory or BufferMemory()

        # Context
        self.context = Context(agent_name=name)
        if keypair:
            self.context.agent_keypair_fingerprint = keypair.fingerprint

    def _get_tools_schema(self) -> list[dict[str, Any]]:
        """Retorna schemas das tools no formato do provider."""
        schemas = []
        for tool in self.tools:
            if isinstance(tool, Tool):
                schemas.append(tool.to_openai_schema())
        return schemas

    async def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Executa uma tool por nome."""
        for tool in self.tools:
            if isinstance(tool, Tool) and tool.name == tool_name:
                # Security check
                if self.keypair and self.permissions:
                    if not self.permissions.can_access(self.keypair.fingerprint, "tool", tool_name):
                        return f"❌ Acesso negado à tool '{tool_name}'. Permissão insuficiente."

                result = await tool.execute(**arguments)
                if result.success:
                    return str(result.result)
                return f"Erro: {result.error}"

        return f"Tool '{tool_name}' não encontrada."

    async def run(
        self,
        prompt: str,
        inputs: Optional[list[Any]] = None,
        **kwargs: Any,
    ) -> Response:
        """Executa o agente com o prompt dado.

        Args:
            prompt: Pergunta ou tarefa para o agente.
            inputs: Inputs multi-modal (arquivos, URLs, etc.).

        Returns:
            Response com conteúdo e metadados.
        """
        provider = self._resolved_provider or self.provider_instance
        if not provider:
            raise OmniaError(
                "Nenhum provider configurado para o agente.",
                suggestion="Passe um provider: Agent(provider=Anthropic())",
            )

        # Carregar inputs
        if inputs:
            loaded = await AutoLoader.load([str(i) for i in inputs])
            content_parts = [prompt] + [f"[{c.type.value}: {str(c.data)[:500]}]" for c in loaded]
            user_msg = Message.user("\n".join(content_parts))
        else:
            user_msg = Message.user(prompt)

        # Montar mensagens
        messages = [Message.system(self.system_prompt)]
        history = await self.memory.get_messages(limit=50)
        messages.extend(history)
        messages.append(user_msg)
        await self.memory.add(user_msg)

        # Loop de raciocínio com tool calling
        total_usage = Usage()

        for iteration in range(self.max_iterations):
            tools_schema = self._get_tools_schema() if self.tools else None

            response = await provider.complete(
                messages,
                tools=tools_schema,
                **kwargs,
            )
            total_usage = total_usage + response.usage

            if response.has_tool_calls:
                # Montar assistant message com tool_calls para OpenAI format
                assistant_msg = Message.assistant(response.content or "")
                assistant_msg.metadata["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ]
                messages.append(assistant_msg)

                for tc in response.tool_calls:
                    logger.debug(f"Tool call: {tc.name}", args=tc.arguments)
                    result = await self._execute_tool(tc.name, tc.arguments)
                    messages.append(Message.tool(tc.name, result, tc.id))
                    logger.debug(f"Tool result: {tc.name}", result=result[:100])
            else:
                # Resposta final
                response.usage = total_usage
                assistant_msg = Message.assistant(response.content)
                await self.memory.add(assistant_msg)
                return response

        # Se atingiu max_iterations
        response.usage = total_usage
        return response

    async def stream(self, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:
        """Streaming de resposta (sem tool calling)."""
        provider = self._resolved_provider or self.provider_instance
        if not provider:
            yield "Erro: nenhum provider configurado."
            return

        messages = [Message.system(self.system_prompt), Message.user(prompt)]
        async for token in provider.stream(messages, **kwargs):
            yield token


# Alias para simplicidade
Agent = BaseAgent
