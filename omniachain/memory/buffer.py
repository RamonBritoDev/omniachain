"""
OmniaChain — BufferMemory: histórico completo em memória.

Exemplo::

    memory = BufferMemory(max_messages=100)
    await memory.add(Message.user("Olá"))
    messages = await memory.get_messages()
"""

from __future__ import annotations

from typing import Optional

from omniachain.core.message import Message


class BufferMemory:
    """Memória em buffer — mantém histórico completo de mensagens em RAM.

    Exemplo::

        memory = BufferMemory(max_messages=50)
        await memory.add(Message.user("Pergunta"))
        await memory.add(Message.assistant("Resposta"))
        msgs = await memory.get_messages()
    """

    def __init__(self, max_messages: int = 1000) -> None:
        self.max_messages = max_messages
        self._messages: list[Message] = []

    async def add(self, message: Message) -> None:
        """Adiciona uma mensagem ao buffer."""
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            # Mantém system messages + últimas N
            system = [m for m in self._messages if m.role.value == "system"]
            others = [m for m in self._messages if m.role.value != "system"]
            keep = self.max_messages - len(system)
            self._messages = system + others[-keep:]

    async def get_messages(self, limit: Optional[int] = None) -> list[Message]:
        """Retorna mensagens do buffer."""
        if limit:
            return self._messages[-limit:]
        return list(self._messages)

    async def clear(self) -> None:
        """Limpa todas as mensagens."""
        self._messages.clear()

    async def search(self, query: str, limit: int = 5) -> list[Message]:
        """Busca mensagens por texto (busca simples por substring)."""
        results = []
        for msg in reversed(self._messages):
            if query.lower() in msg.text.lower():
                results.append(msg)
                if len(results) >= limit:
                    break
        return results

    @property
    def size(self) -> int:
        """Número de mensagens no buffer."""
        return len(self._messages)

    def __repr__(self) -> str:
        return f"BufferMemory(messages={len(self._messages)}, max={self.max_messages})"
