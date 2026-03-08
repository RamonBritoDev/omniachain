"""
OmniaChain — Middleware de segurança que intercepta chamadas.

Valida assinatura PGP + permissões antes de executar tools/memória.

Exemplo::

    middleware = SecurityMiddleware(permissions=perms)
    await middleware.validate_request(
        keypair=agent_keys,
        resource_type="tool",
        resource_name="web_search",
        payload=b"parâmetros da chamada",
    )
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from pydantic import BaseModel, Field

from omniachain.core.errors import SecurityError
from omniachain.security.keypair import KeyPair
from omniachain.security.permissions import Permissions


class SecurityRequest(BaseModel):
    """Requisição assinada para validação."""

    agent_name: str
    fingerprint: str
    resource_type: str
    resource_name: str
    timestamp: float = Field(default_factory=time.time)
    signature: str = ""
    payload_hash: str = ""


class SecurityMiddleware:
    """Middleware que intercepta chamadas e valida segurança.

    Fluxo:
    1. Agente assina a requisição com chave privada PGP
    2. Middleware verifica assinatura
    3. Middleware checa permissões
    4. Se válido, executa operação

    Exemplo::

        middleware = SecurityMiddleware(permissions=perms)

        # Antes de executar uma tool:
        await middleware.validate_request(
            keypair=keys,
            resource_type="tool",
            resource_name="web_search",
            payload=b"query=python",
        )
    """

    def __init__(
        self,
        permissions: Optional[Permissions] = None,
        enabled: bool = True,
        max_request_age_seconds: float = 300.0,
    ) -> None:
        self.permissions = permissions or Permissions()
        self.enabled = enabled
        self.max_request_age_seconds = max_request_age_seconds
        self._audit_log: list[dict[str, Any]] = []

    async def validate_request(
        self,
        keypair: KeyPair,
        resource_type: str,
        resource_name: str,
        payload: bytes = b"",
    ) -> SecurityRequest:
        """Valida uma requisição assinada.

        Args:
            keypair: Par de chaves do agente.
            resource_type: Tipo do recurso.
            resource_name: Nome do recurso.
            payload: Dados da requisição.

        Returns:
            SecurityRequest validado.

        Raises:
            SecurityError: Se a validação falhar.
        """
        if not self.enabled:
            return SecurityRequest(
                agent_name=keypair.agent_name,
                fingerprint=keypair.fingerprint,
                resource_type=resource_type,
                resource_name=resource_name,
            )

        # 1. Criar request
        import hashlib
        payload_hash = hashlib.sha256(payload).hexdigest()

        request = SecurityRequest(
            agent_name=keypair.agent_name,
            fingerprint=keypair.fingerprint,
            resource_type=resource_type,
            resource_name=resource_name,
            payload_hash=payload_hash,
        )

        # 2. Assinar
        sign_data = f"{request.fingerprint}:{request.resource_type}:{request.resource_name}:{request.timestamp}:{payload_hash}"
        request.signature = await keypair.sign(sign_data.encode())

        # 3. Verificar assinatura
        is_valid = await keypair.verify(sign_data.encode(), request.signature)
        if not is_valid:
            self._log_audit(request, "DENIED", "Assinatura PGP inválida")
            raise SecurityError(
                "Assinatura PGP inválida.",
                agent_name=keypair.agent_name,
                resource=f"{resource_type}:{resource_name}",
                suggestion="Verifique se o KeyPair do agente está correto.",
            )

        # 4. Verificar timestamp (anti-replay)
        age = time.time() - request.timestamp
        if age > self.max_request_age_seconds:
            self._log_audit(request, "DENIED", "Requisição expirada")
            raise SecurityError(
                f"Requisição expirada ({age:.0f}s). Máximo: {self.max_request_age_seconds}s.",
                agent_name=keypair.agent_name,
                resource=f"{resource_type}:{resource_name}",
                suggestion="Gere uma nova requisição.",
            )

        # 5. Verificar permissão
        if not self.permissions.can_access(keypair.fingerprint, resource_type, resource_name):
            self._log_audit(request, "DENIED", "Sem permissão")
            raise SecurityError(
                f"Agente '{keypair.agent_name}' não tem permissão para {resource_type} '{resource_name}'.",
                agent_name=keypair.agent_name,
                resource=f"{resource_type}:{resource_name}",
            )

        self._log_audit(request, "ALLOWED", "Validação OK")
        return request

    async def create_signed_request(
        self,
        keypair: KeyPair,
        resource_type: str,
        resource_name: str,
        payload: bytes = b"",
    ) -> dict[str, str]:
        """Cria uma requisição assinada para envio.

        Returns:
            Dict com dados da requisição assinada.
        """
        import hashlib

        timestamp = time.time()
        payload_hash = hashlib.sha256(payload).hexdigest()
        sign_data = f"{keypair.fingerprint}:{resource_type}:{resource_name}:{timestamp}:{payload_hash}"
        signature = await keypair.sign(sign_data.encode())

        return {
            "agent_name": keypair.agent_name,
            "fingerprint": keypair.fingerprint,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "timestamp": str(timestamp),
            "payload_hash": payload_hash,
            "signature": signature,
        }

    def _log_audit(self, request: SecurityRequest, decision: str, reason: str) -> None:
        """Registra no log de auditoria."""
        entry = {
            "timestamp": time.time(),
            "agent": request.agent_name,
            "fingerprint": request.fingerprint[:16] + "...",
            "resource": f"{request.resource_type}:{request.resource_name}",
            "decision": decision,
            "reason": reason,
        }
        self._audit_log.append(entry)

        # Manter últimas 1000 entradas
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retorna as últimas entradas do log de auditoria."""
        return self._audit_log[-limit:]
