"""OmniaChain — Coordinator: comunicação entre agentes."""

from __future__ import annotations

import asyncio
from typing import Any, Optional


class AgentMessage:
    """Mensagem entre agentes."""
    def __init__(self, from_agent: str, to_agent: str, content: str, metadata: dict[str, Any] | None = None):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.content = content
        self.metadata = metadata or {}


class Coordinator:
    """Coordena comunicação entre múltiplos agentes.

    Exemplo::

        coord = Coordinator()
        coord.register("researcher")
        coord.register("analyst")
        await coord.send("researcher", "analyst", "Dados coletados: ...")
        msg = await coord.receive("analyst")
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = {}
        self._broadcast_log: list[AgentMessage] = []

    def register(self, agent_name: str) -> None:
        """Registra um agente para comunicação."""
        if agent_name not in self._queues:
            self._queues[agent_name] = asyncio.Queue()

    async def send(self, from_agent: str, to_agent: str, content: str, **metadata: Any) -> None:
        """Envia mensagem de um agente para outro."""
        msg = AgentMessage(from_agent, to_agent, content, metadata)
        if to_agent in self._queues:
            await self._queues[to_agent].put(msg)
        self._broadcast_log.append(msg)

    async def receive(self, agent_name: str, timeout: float = 30.0) -> Optional[AgentMessage]:
        """Recebe a próxima mensagem para um agente."""
        if agent_name not in self._queues:
            return None
        try:
            return await asyncio.wait_for(self._queues[agent_name].get(), timeout)
        except asyncio.TimeoutError:
            return None

    async def broadcast(self, from_agent: str, content: str, **metadata: Any) -> None:
        """Envia mensagem para todos os agentes registrados."""
        for name in self._queues:
            if name != from_agent:
                await self.send(from_agent, name, content, **metadata)

    @property
    def agents(self) -> list[str]:
        return list(self._queues.keys())
