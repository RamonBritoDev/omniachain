"""
OmniaChain — Session: sessão unificada multi-agent/multi-API.

Exemplo::

    async with Session() as session:
        session.register_provider("smart", Anthropic())
        session.register_provider("fast", Groq())
        session.register_agent(researcher)
        result = await session.run("Pesquise e analise tendências de IA")
"""

from __future__ import annotations

import time
import uuid
from typing import Any, AsyncGenerator, Literal, Optional

from pydantic import BaseModel, Field

from omniachain.core.context import Context
from omniachain.core.errors import OrchestrationError
from omniachain.core.message import Message
from omniachain.core.response import Response, Usage
from omniachain.loaders.auto import AutoLoader
from omniachain.orchestration.coordinator import Coordinator
from omniachain.providers.base import BaseProvider


class SessionResult(BaseModel):
    """Resultado de uma sessão multi-agente."""

    final_output: str = ""
    agents_used: list[str] = Field(default_factory=list)
    total_cost: float = 0.0
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    session_id: str = ""
    steps: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Session:
    """Sessão unificada para orquestração multi-agent/multi-API.

    Exemplo::

        async with Session() as session:
            session.register_provider("smart", Anthropic("claude-3-5-sonnet"))
            session.register_provider("fast", Groq("llama-3"))

            researcher = ReActAgent(provider="smart", tools=[web_search])
            writer = PlannerAgent(provider="fast", tools=[file])

            session.register_agent(researcher)
            session.register_agent(writer)

            result = await session.run(
                goal="Pesquise IA e escreva um relatório",
                strategy="sequential"
            )
    """

    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self._providers: dict[str, BaseProvider] = {}
        self._agents: list[Any] = []
        self._coordinator = Coordinator()
        self._context = Context(session_id=self.session_id)

    async def __aenter__(self) -> Session:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def register_provider(self, alias: str, provider: BaseProvider) -> None:
        """Registra um provider com um alias."""
        self._providers[alias] = provider

    def register_agent(self, agent: Any) -> None:
        """Registra um agente na sessão."""
        self._agents.append(agent)
        name = getattr(agent, "name", f"agent_{len(self._agents)}")
        self._coordinator.register(name)

    def register_agents(self, *agents: Any) -> None:
        """Registra múltiplos agentes."""
        for agent in agents:
            self.register_agent(agent)

    def get_provider(self, alias: str) -> BaseProvider:
        """Obtém provider por alias."""
        if alias not in self._providers:
            raise OrchestrationError(
                f"Provider '{alias}' não registrado na sessão.",
                session_id=self.session_id,
            )
        return self._providers[alias]

    async def run(
        self,
        goal: str,
        inputs: Optional[list[Any]] = None,
        strategy: Literal["auto", "sequential", "parallel", "supervisor"] = "auto",
    ) -> SessionResult:
        """Executa a sessão com a estratégia escolhida.

        Args:
            goal: Objetivo principal da sessão.
            inputs: Inputs multi-modal (arquivos, URLs, etc.).
            strategy: Estratégia de orquestração.
        """
        start = time.perf_counter()
        result = SessionResult(session_id=self.session_id)

        # Carregar inputs
        if inputs:
            loaded = await AutoLoader.load([str(i) for i in inputs])
            self._context.set("inputs", loaded)

        self._context.set("goal", goal)

        if not self._agents:
            raise OrchestrationError(
                "Nenhum agente registrado na sessão.",
                session_id=self.session_id,
                suggestion="Registre agentes com session.register_agent(agent).",
            )

        # Resolver providers dos agentes
        for agent in self._agents:
            provider_alias = getattr(agent, "provider", None)
            if isinstance(provider_alias, str) and provider_alias in self._providers:
                agent._resolved_provider = self._providers[provider_alias]

        # Executar estratégia
        if strategy == "sequential" or (strategy == "auto" and len(self._agents) <= 3):
            result = await self._run_sequential(goal, result)
        elif strategy == "parallel":
            result = await self._run_parallel(goal, result)
        else:
            result = await self._run_sequential(goal, result)

        result.total_latency_ms = (time.perf_counter() - start) * 1000
        return result

    async def _run_sequential(self, goal: str, result: SessionResult) -> SessionResult:
        """Executa agentes em sequência, passando output do anterior como input."""
        current_input = goal
        total_usage = Usage()

        for agent in self._agents:
            agent_name = getattr(agent, "name", "unknown")
            try:
                # Resolver provider
                provider = getattr(agent, "_resolved_provider", None) or getattr(agent, "provider_instance", None)
                if provider and isinstance(provider, BaseProvider):
                    response = await provider.complete(
                        [Message.user(current_input)],
                        tools=[t.to_openai_schema() for t in getattr(agent, "tools", []) if hasattr(t, "to_openai_schema")],
                    )
                    current_input = response.content
                    total_usage = total_usage + response.usage
                    result.agents_used.append(agent_name)
                    result.steps.append({
                        "agent": agent_name,
                        "output": response.content[:200],
                        "tokens": response.usage.total_tokens,
                        "cost": response.usage.cost,
                    })
                else:
                    # Tentar run() direto se o agente suportar
                    if hasattr(agent, "run"):
                        response = await agent.run(current_input)
                        current_input = str(response) if not isinstance(response, str) else response
                        result.agents_used.append(agent_name)

            except Exception as e:
                result.steps.append({
                    "agent": agent_name,
                    "error": str(e),
                })

        result.final_output = current_input
        result.total_cost = total_usage.cost
        result.total_tokens = total_usage.total_tokens
        return result

    async def _run_parallel(self, goal: str, result: SessionResult) -> SessionResult:
        """Executa todos os agentes em paralelo com o mesmo input."""
        import asyncio

        async def _run_agent(agent: Any) -> tuple[str, str]:
            agent_name = getattr(agent, "name", "unknown")
            try:
                provider = getattr(agent, "_resolved_provider", None)
                if provider and isinstance(provider, BaseProvider):
                    response = await provider.complete([Message.user(goal)])
                    return agent_name, response.content
                elif hasattr(agent, "run"):
                    resp = await agent.run(goal)
                    return agent_name, str(resp)
            except Exception as e:
                return agent_name, f"Erro: {e}"
            return agent_name, ""

        tasks = [_run_agent(a) for a in self._agents]
        outputs = await asyncio.gather(*tasks)

        # Combinar outputs
        combined = []
        for name, output in outputs:
            result.agents_used.append(name)
            combined.append(f"## {name}\n{output}")
            result.steps.append({"agent": name, "output": output[:200]})

        result.final_output = "\n\n".join(combined)
        return result

    async def stream(self, goal: str, inputs: Optional[list[Any]] = None) -> AsyncGenerator[str, None]:
        """Streaming da sessão (usa o primeiro agente)."""
        if not self._agents:
            yield "Nenhum agente registrado."
            return

        agent = self._agents[0]
        provider = getattr(agent, "_resolved_provider", None)
        if provider and isinstance(provider, BaseProvider):
            async for token in provider.stream([Message.user(goal)]):
                yield token
