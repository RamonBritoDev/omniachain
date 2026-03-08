"""
OmniaChain — SummaryMemory: resume históricos longos automaticamente.

Usa um LLM para comprimir conversas antigas em resumos.
"""

from __future__ import annotations

from typing import Any, Optional

from omniachain.core.message import Message


class SummaryMemory:
    """Memória com resumo automático — comprime conversas longas.

    Quando o histórico excede max_messages, as mensagens mais antigas são
    resumidas automaticamente por um LLM.

    Exemplo::

        memory = SummaryMemory(max_messages=20)
        # Após 20 mensagens, as antigas são resumidas automaticamente
    """

    def __init__(
        self,
        max_messages: int = 20,
        provider: Optional[Any] = None,
        summary_prompt: str = "Resuma a conversa abaixo de forma concisa, mantendo os pontos principais:\n\n{conversation}",
    ) -> None:
        self.max_messages = max_messages
        self.provider = provider
        self.summary_prompt = summary_prompt
        self._messages: list[Message] = []
        self._summaries: list[str] = []

    async def add(self, message: Message) -> None:
        """Adiciona mensagem e resume se necessário."""
        self._messages.append(message)

        if len(self._messages) > self.max_messages:
            await self._summarize_oldest()

    async def get_messages(self, limit: Optional[int] = None) -> list[Message]:
        """Retorna mensagens com resumo como primeira mensagem de contexto."""
        result: list[Message] = []

        # Adicionar resumos como contexto
        if self._summaries:
            summary_text = "\n\n---\n\n".join(self._summaries)
            result.append(Message.system(f"Resumo da conversa anterior:\n{summary_text}"))

        msgs = self._messages[-limit:] if limit else self._messages
        result.extend(msgs)
        return result

    async def _summarize_oldest(self) -> None:
        """Resume as mensagens mais antigas."""
        # Pegar metade mais antiga para resumir
        split = len(self._messages) // 2
        to_summarize = self._messages[:split]
        self._messages = self._messages[split:]

        # Montar texto da conversa
        conversation = "\n".join(
            f"{m.role.value}: {m.text}" for m in to_summarize
        )

        if self.provider:
            # Usar LLM para resumir
            prompt = self.summary_prompt.format(conversation=conversation)
            from omniachain.core.message import Message as Msg
            response = await self.provider.complete([Msg.user(prompt)])
            summary = response.content
        else:
            # Fallback: resumo simples (últimas linhas)
            lines = conversation.split("\n")
            summary = f"[Resumo de {len(to_summarize)} mensagens]\n" + "\n".join(lines[-10:])

        self._summaries.append(summary)

    async def clear(self) -> None:
        """Limpa mensagens e resumos."""
        self._messages.clear()
        self._summaries.clear()

    async def search(self, query: str, limit: int = 5) -> list[Message]:
        """Busca em mensagens e resumos."""
        results = []
        for msg in reversed(self._messages):
            if query.lower() in msg.text.lower():
                results.append(msg)
                if len(results) >= limit:
                    break
        return results

    @property
    def summary_count(self) -> int:
        return len(self._summaries)

    def __repr__(self) -> str:
        return f"SummaryMemory(messages={len(self._messages)}, summaries={len(self._summaries)})"
