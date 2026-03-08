"""
OmniaChain — Contexto compartilhado entre steps de execução.

O contexto carrega dados, mensagens e metadados entre etapas de um pipeline
ou agente, incluindo variáveis compartilhadas e histórico.

Exemplo de uso::

    ctx = Context()
    ctx.set("query", "Qual o PIB do Brasil?")
    ctx.messages.append(Message.user("Olá"))
    print(ctx.get("query"))  # "Qual o PIB do Brasil?"
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from omniachain.core.message import Message
from omniachain.core.response import Usage


class Context(BaseModel):
    """Contexto compartilhado durante a execução de chains, pipelines e agentes.

    Armazena mensagens, variáveis, metadados e tracking de uso.
    É passado entre steps para compartilhar estado.

    Exemplo::

        ctx = Context(session_id="abc123")
        ctx.set("user_input", "Analise este PDF")
        ctx.messages.append(Message.user("..."))

        # Em outro step:
        user_input = ctx.get("user_input")
    """

    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Mensagens do histórico ──
    messages: list[Message] = Field(default_factory=list)

    # ── Variáveis compartilhadas ──
    variables: dict[str, Any] = Field(default_factory=dict)

    # ── Uso acumulado ──
    total_usage: Usage = Field(default_factory=Usage)

    # ── Metadados livres ──
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ── Agent info ──
    agent_name: Optional[str] = None
    agent_keypair_fingerprint: Optional[str] = None

    def set(self, key: str, value: Any) -> None:
        """Define uma variável no contexto.

        Args:
            key: Nome da variável.
            value: Valor a armazenar.
        """
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém uma variável do contexto.

        Args:
            key: Nome da variável.
            default: Valor padrão se não existir.
        """
        return self.variables.get(key, default)

    def has(self, key: str) -> bool:
        """Verifica se uma variável existe no contexto."""
        return key in self.variables

    def add_message(self, message: Message) -> None:
        """Adiciona uma mensagem ao histórico."""
        self.messages.append(message)

    def add_usage(self, usage: Usage) -> None:
        """Acumula métricas de uso de tokens."""
        self.total_usage = self.total_usage + usage

    def get_messages_for_provider(self, max_messages: Optional[int] = None) -> list[Message]:
        """Retorna mensagens formatadas para envio ao provider.

        Args:
            max_messages: Limite máximo de mensagens. None = todas.
        """
        msgs = self.messages
        if max_messages and len(msgs) > max_messages:
            # Sempre mantém a primeira mensagem (system) e as últimas N
            system_msgs = [m for m in msgs if m.role.value == "system"]
            other_msgs = [m for m in msgs if m.role.value != "system"]
            msgs = system_msgs + other_msgs[-(max_messages - len(system_msgs)):]
        return msgs

    @property
    def last_message(self) -> Optional[Message]:
        """Retorna a última mensagem do histórico."""
        return self.messages[-1] if self.messages else None

    @property
    def message_count(self) -> int:
        """Retorna o número de mensagens no histórico."""
        return len(self.messages)

    def fork(self, new_trace_id: Optional[str] = None) -> Context:
        """Cria uma cópia do contexto com novo trace_id.

        Útil para execução paralela de sub-tarefas.
        """
        return Context(
            session_id=self.session_id,
            trace_id=new_trace_id or uuid.uuid4().hex[:16],
            messages=list(self.messages),
            variables=dict(self.variables),
            total_usage=self.total_usage.model_copy(),
            metadata=dict(self.metadata),
            agent_name=self.agent_name,
            agent_keypair_fingerprint=self.agent_keypair_fingerprint,
        )

    def clear_messages(self) -> None:
        """Limpa o histórico de mensagens."""
        self.messages.clear()

    def clear_variables(self) -> None:
        """Limpa todas as variáveis."""
        self.variables.clear()

    model_config = {"arbitrary_types_allowed": True}
