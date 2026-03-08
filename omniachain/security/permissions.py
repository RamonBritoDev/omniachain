"""
OmniaChain — Sistema de permissões para tools e memória.

Define quais resources cada agente pode acessar.

Exemplo::

    perms = Permissions()
    perms.grant("fingerprint-abc", tools=["web_search", "calculator"])
    perms.deny("fingerprint-abc", tools=["code_exec"])
    
    perms.can_access("fingerprint-abc", "tool", "web_search")  # True
    perms.can_access("fingerprint-abc", "tool", "code_exec")   # False
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AccessLevel(str, Enum):
    """Níveis de acesso."""
    ALLOW = "allow"
    DENY = "deny"


class Permission(BaseModel):
    """Uma permissão individual.

    Attributes:
        resource_type: Tipo do recurso (tool, memory, provider).
        resource_name: Nome específico do recurso.
        access: Nível de acesso (allow/deny).
    """

    resource_type: str  # "tool", "memory", "provider", "*"
    resource_name: str  # nome específico ou "*" para todos
    access: AccessLevel = AccessLevel.ALLOW

    def matches(self, resource_type: str, resource_name: str) -> bool:
        """Verifica se esta permissão se aplica ao recurso."""
        type_match = self.resource_type == "*" or self.resource_type == resource_type
        name_match = self.resource_name == "*" or self.resource_name == resource_name
        return type_match and name_match


class Permissions:
    """Gerenciador de permissões por agente (via fingerprint PGP).

    Exemplo::

        perms = Permissions()
        perms.grant("agent-fp", tools=["web_search"])
        perms.grant("agent-fp", memory=["read", "write"])

        assert perms.can_access("agent-fp", "tool", "web_search")
        assert not perms.can_access("agent-fp", "tool", "code_exec")
    """

    def __init__(self, default_policy: AccessLevel = AccessLevel.DENY) -> None:
        self._rules: dict[str, list[Permission]] = {}
        self.default_policy = default_policy

    def grant(
        self,
        fingerprint: str,
        *,
        tools: Optional[list[str]] = None,
        memory: Optional[list[str]] = None,
        providers: Optional[list[str]] = None,
        all_resources: bool = False,
    ) -> None:
        """Concede permissão a um agente.

        Args:
            fingerprint: Fingerprint PGP do agente.
            tools: Lista de nomes de tools permitidas.
            memory: Lista de operações de memória permitidas (read, write, delete).
            providers: Lista de providers permitidos.
            all_resources: Se True, permite acesso a tudo.
        """
        if fingerprint not in self._rules:
            self._rules[fingerprint] = []

        if all_resources:
            self._rules[fingerprint].append(
                Permission(resource_type="*", resource_name="*", access=AccessLevel.ALLOW)
            )
            return

        for tool_name in (tools or []):
            self._rules[fingerprint].append(
                Permission(resource_type="tool", resource_name=tool_name, access=AccessLevel.ALLOW)
            )
        for mem_op in (memory or []):
            self._rules[fingerprint].append(
                Permission(resource_type="memory", resource_name=mem_op, access=AccessLevel.ALLOW)
            )
        for prov in (providers or []):
            self._rules[fingerprint].append(
                Permission(resource_type="provider", resource_name=prov, access=AccessLevel.ALLOW)
            )

    def deny(
        self,
        fingerprint: str,
        *,
        tools: Optional[list[str]] = None,
        memory: Optional[list[str]] = None,
        providers: Optional[list[str]] = None,
    ) -> None:
        """Nega permissão a um agente.

        Args:
            fingerprint: Fingerprint PGP do agente.
            tools: Lista de tools negadas.
            memory: Lista de operações de memória negadas.
            providers: Lista de providers negados.
        """
        if fingerprint not in self._rules:
            self._rules[fingerprint] = []

        for tool_name in (tools or []):
            self._rules[fingerprint].append(
                Permission(resource_type="tool", resource_name=tool_name, access=AccessLevel.DENY)
            )
        for mem_op in (memory or []):
            self._rules[fingerprint].append(
                Permission(resource_type="memory", resource_name=mem_op, access=AccessLevel.DENY)
            )
        for prov in (providers or []):
            self._rules[fingerprint].append(
                Permission(resource_type="provider", resource_name=prov, access=AccessLevel.DENY)
            )

    def can_access(self, fingerprint: str, resource_type: str, resource_name: str) -> bool:
        """Verifica se um agente pode acessar um recurso.

        Regras são avaliadas na ordem: DENY tem prioridade sobre ALLOW.

        Args:
            fingerprint: Fingerprint PGP do agente.
            resource_type: Tipo do recurso (tool, memory, provider).
            resource_name: Nome do recurso.

        Returns:
            True se o acesso é permitido.
        """
        rules = self._rules.get(fingerprint, [])

        if not rules:
            return self.default_policy == AccessLevel.ALLOW

        # Verificar regras específicas (deny tem prioridade)
        has_explicit_allow = False

        for rule in rules:
            if rule.matches(resource_type, resource_name):
                if rule.access == AccessLevel.DENY:
                    return False
                if rule.access == AccessLevel.ALLOW:
                    has_explicit_allow = True

        if has_explicit_allow:
            return True

        return self.default_policy == AccessLevel.ALLOW

    def get_allowed_resources(self, fingerprint: str, resource_type: str) -> list[str]:
        """Lista todos os recursos permitidos de um tipo para um agente."""
        rules = self._rules.get(fingerprint, [])
        allowed = set()
        denied = set()

        for rule in rules:
            if rule.resource_type in (resource_type, "*"):
                if rule.access == AccessLevel.ALLOW:
                    allowed.add(rule.resource_name)
                else:
                    denied.add(rule.resource_name)

        return sorted(allowed - denied)

    def remove_agent(self, fingerprint: str) -> None:
        """Remove todas as permissões de um agente."""
        self._rules.pop(fingerprint, None)
