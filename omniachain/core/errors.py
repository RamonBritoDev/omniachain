"""
OmniaChain — Sistema de erros com contexto completo.

Cada erro informa O QUE falhou, ONDE e COMO corrigir via campo `suggestion`.

Exemplo de uso::

    try:
        await provider.complete(messages)
    except ProviderError as e:
        print(e.suggestion)  # "Verifique se ANTHROPIC_API_KEY está configurada"
"""

from __future__ import annotations

import traceback
from typing import Any, Optional


class OmniaError(Exception):
    """Erro base do OmniaChain. Todos os erros herdam desta classe.

    Attributes:
        message: Descrição do erro.
        suggestion: Como corrigir o problema.
        context: Dicionário com contexto adicional (provider, tool, etc.).
        original_error: Exceção original que causou este erro.
    """

    def __init__(
        self,
        message: str,
        *,
        suggestion: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        self.message = message
        self.suggestion = suggestion or "Sem sugestão disponível."
        self.context = context or {}
        self.original_error = original_error
        super().__init__(self._format())

    def _format(self) -> str:
        parts = [f"[OmniaChain] {self.message}"]
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            parts.append(f"  Contexto: {ctx_str}")
        parts.append(f"  Sugestão: {self.suggestion}")
        if self.original_error:
            parts.append(f"  Causa: {type(self.original_error).__name__}: {self.original_error}")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serializa o erro para logging estruturado."""
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "suggestion": self.suggestion,
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None,
            "traceback": traceback.format_exc() if self.original_error else None,
        }


class ProviderError(OmniaError):
    """Erro ao comunicar com um provider de IA (OpenAI, Anthropic, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "unknown",
        model: str = "unknown",
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            suggestion=suggestion or f"Verifique a API key e conectividade do provider '{provider}'.",
            context={"provider": provider, "model": model},
            original_error=original_error,
        )


class LoaderError(OmniaError):
    """Erro ao carregar ou processar um arquivo/input."""

    def __init__(
        self,
        message: str,
        *,
        loader: str = "unknown",
        source: str = "unknown",
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            suggestion=suggestion or f"Verifique se o arquivo '{source}' existe e é acessível.",
            context={"loader": loader, "source": source},
            original_error=original_error,
        )


class ToolError(OmniaError):
    """Erro durante execução de uma tool."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: str = "unknown",
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            suggestion=suggestion or f"Verifique os parâmetros passados para a tool '{tool_name}'.",
            context={"tool": tool_name},
            original_error=original_error,
        )


class SecurityError(OmniaError):
    """Erro de autenticação ou autorização (PGP, permissões)."""

    def __init__(
        self,
        message: str,
        *,
        agent_name: str = "unknown",
        resource: str = "unknown",
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            suggestion=suggestion or f"O agente '{agent_name}' não tem permissão para acessar '{resource}'.",
            context={"agent": agent_name, "resource": resource},
            original_error=original_error,
        )


class MemoryError(OmniaError):
    """Erro ao acessar ou manipular memória."""

    def __init__(
        self,
        message: str,
        *,
        memory_type: str = "unknown",
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            suggestion=suggestion or "Verifique a conexão com o backend de memória.",
            context={"memory_type": memory_type},
            original_error=original_error,
        )


class PipelineError(OmniaError):
    """Erro durante execução de um pipeline."""

    def __init__(
        self,
        message: str,
        *,
        step: str = "unknown",
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            suggestion=suggestion or f"Verifique a configuração do step '{step}' no pipeline.",
            context={"step": step},
            original_error=original_error,
        )


class OrchestrationError(OmniaError):
    """Erro na orquestração de agentes ou sessões."""

    def __init__(
        self,
        message: str,
        *,
        session_id: Optional[str] = None,
        suggestion: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            message,
            suggestion=suggestion or "Verifique a configuração da sessão e dos agentes registrados.",
            context={"session_id": session_id},
            original_error=original_error,
        )
