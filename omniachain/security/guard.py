"""
OmniaChain — Security Guard: decorator para proteger tools e memória.

Exemplo::

    @requires_permission("tool", "web_search")
    async def web_search(query: str) -> str:
        ...
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional

from omniachain.core.errors import SecurityError
from omniachain.security.permissions import Permissions


class SecurityGuard:
    """Guarda de segurança que valida assinatura PGP e permissões.

    Exemplo::

        guard = SecurityGuard(permissions=perms)
        guard.check_access(fingerprint="abc", resource_type="tool", resource_name="web_search")
    """

    def __init__(self, permissions: Optional[Permissions] = None, enabled: bool = True) -> None:
        self.permissions = permissions or Permissions()
        self.enabled = enabled

    def check_access(
        self,
        fingerprint: str,
        resource_type: str,
        resource_name: str,
        agent_name: str = "unknown",
    ) -> bool:
        """Verifica se o agente tem acesso ao recurso.

        Args:
            fingerprint: Fingerprint PGP do agente.
            resource_type: Tipo do recurso (tool, memory).
            resource_name: Nome do recurso.
            agent_name: Nome do agente para mensagens de erro.

        Returns:
            True se permitido.

        Raises:
            SecurityError: Se o acesso é negado.
        """
        if not self.enabled:
            return True

        if not self.permissions.can_access(fingerprint, resource_type, resource_name):
            raise SecurityError(
                f"Acesso negado: agente '{agent_name}' não pode acessar {resource_type} '{resource_name}'.",
                agent_name=agent_name,
                resource=f"{resource_type}:{resource_name}",
                suggestion=f"Conceda permissão com: permissions.grant('{fingerprint}', {resource_type}s=['{resource_name}'])",
            )

        return True


# Guard global (configurável)
_global_guard: Optional[SecurityGuard] = None


def set_global_guard(guard: SecurityGuard) -> None:
    """Define o guard de segurança global."""
    global _global_guard
    _global_guard = guard


def get_global_guard() -> Optional[SecurityGuard]:
    """Retorna o guard de segurança global."""
    return _global_guard


def requires_permission(
    resource_type: str,
    resource_name: str,
) -> Callable:
    """Decorator que protege uma função com verificação de permissão PGP.

    O contexto do agente (fingerprint) é extraído dos kwargs ou do contexto global.

    Exemplo::

        @requires_permission("tool", "web_search")
        async def web_search(query: str, _agent_fingerprint: str = "") -> str:
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            guard = _global_guard
            if guard and guard.enabled:
                fingerprint = kwargs.pop("_agent_fingerprint", "")
                agent_name = kwargs.pop("_agent_name", "unknown")

                if fingerprint:
                    guard.check_access(
                        fingerprint=fingerprint,
                        resource_type=resource_type,
                        resource_name=resource_name,
                        agent_name=agent_name,
                    )

            return await func(*args, **kwargs)

        wrapper._security_resource_type = resource_type  # type: ignore
        wrapper._security_resource_name = resource_name  # type: ignore
        return wrapper

    return decorator
