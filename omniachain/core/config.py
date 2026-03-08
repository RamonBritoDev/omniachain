"""
OmniaChain — Configuração global do framework.

Carrega settings de variáveis de ambiente e permite override programático.

Exemplo de uso::

    from omniachain.core.config import get_config

    config = get_config()
    config.default_provider = "anthropic"
    config.log_level = "DEBUG"
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Níveis de log suportados."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Formatos de saída de log."""
    TEXT = "text"
    JSON = "json"


class OmniaConfig(BaseModel):
    """Configuração global do OmniaChain.

    Todas as configurações podem ser definidas via variáveis de ambiente
    prefixadas com ``OMNIA_`` ou programaticamente.

    Exemplo::

        config = get_config()
        config.default_provider = "openai"
        config.default_model = "gpt-4o"
    """

    # ── Provider defaults ──
    default_provider: str = Field(
        default_factory=lambda: os.getenv("OMNIA_DEFAULT_PROVIDER", "anthropic"),
        description="Provider padrão para novos agentes.",
    )
    default_model: Optional[str] = Field(
        default_factory=lambda: os.getenv("OMNIA_DEFAULT_MODEL"),
        description="Modelo padrão. None = usar default do provider.",
    )

    # ── API Keys (lidos do env automaticamente) ──
    anthropic_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"),
        description="API key do Anthropic.",
    )
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY"),
        description="API key do OpenAI.",
    )
    groq_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GROQ_API_KEY"),
        description="API key do Groq.",
    )
    google_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY"),
        description="API key do Google (Gemini).",
    )

    # ── Ollama ──
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        description="URL base do servidor Ollama local.",
    )

    # ── Memory / pgvector ──
    pgvector_dsn: Optional[str] = Field(
        default_factory=lambda: os.getenv("OMNIA_PGVECTOR_DSN"),
        description="DSN de conexão PostgreSQL para pgvector (ex: postgresql://user:pass@host/db).",
    )
    memory_backend: str = Field(
        default_factory=lambda: os.getenv("OMNIA_MEMORY_BACKEND", "buffer"),
        description="Backend de memória padrão: buffer, sqlite, pgvector.",
    )

    # ── Security ──
    gpg_home: Optional[str] = Field(
        default_factory=lambda: os.getenv("OMNIA_GPG_HOME"),
        description="Diretório do keyring GPG. None = usar padrão do sistema.",
    )
    security_enabled: bool = Field(
        default_factory=lambda: os.getenv("OMNIA_SECURITY_ENABLED", "false").lower() == "true",
        description="Se True, habilita validação PGP em tools e memória.",
    )

    # ── Observability ──
    log_level: LogLevel = Field(
        default_factory=lambda: LogLevel(os.getenv("OMNIA_LOG_LEVEL", "INFO")),
        description="Nível mínimo de log.",
    )
    log_format: LogFormat = Field(
        default_factory=lambda: LogFormat(os.getenv("OMNIA_LOG_FORMAT", "text")),
        description="Formato de saída dos logs.",
    )
    trace_enabled: bool = Field(
        default_factory=lambda: os.getenv("OMNIA_TRACE_ENABLED", "true").lower() == "true",
        description="Se True, gera traces de execução.",
    )
    cost_tracking: bool = Field(
        default_factory=lambda: os.getenv("OMNIA_COST_TRACKING", "true").lower() == "true",
        description="Se True, rastreia custos de tokens em tempo real.",
    )

    # ── Execution ──
    default_timeout: float = Field(
        default_factory=lambda: float(os.getenv("OMNIA_DEFAULT_TIMEOUT", "30.0")),
        description="Timeout padrão em segundos para chamadas externas.",
    )
    max_retries: int = Field(
        default_factory=lambda: int(os.getenv("OMNIA_MAX_RETRIES", "3")),
        description="Número máximo de retries em caso de falha.",
    )
    max_concurrent: int = Field(
        default_factory=lambda: int(os.getenv("OMNIA_MAX_CONCURRENT", "10")),
        description="Máximo de operações simultâneas em paralelo.",
    )

    model_config = {"validate_default": True}


@lru_cache(maxsize=1)
def get_config() -> OmniaConfig:
    """Retorna a instância singleton de configuração.

    Exemplo::

        config = get_config()
        print(config.default_provider)
    """
    return OmniaConfig()


def reset_config() -> OmniaConfig:
    """Reseta a configuração para os valores padrão. Útil para testes."""
    get_config.cache_clear()
    return get_config()
