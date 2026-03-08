"""OmniaChain — Logger estruturado e legível."""

from __future__ import annotations

import json
import sys
import time
from typing import Any, Optional

from omniachain.core.config import LogFormat, LogLevel, get_config


class OmniaLogger:
    """Logger estruturado do OmniaChain.

    Suporta saída em texto legível ou JSON estruturado.

    Exemplo::

        logger = OmniaLogger("agent.researcher")
        logger.info("Pesquisa iniciada", query="IA generativa")
        logger.error("Falha na API", provider="openai", error="timeout")
    """

    def __init__(self, name: str = "omniachain") -> None:
        self.name = name

    def _should_log(self, level: LogLevel) -> bool:
        config = get_config()
        levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        return levels.index(level) >= levels.index(config.log_level)

    def _format(self, level: str, message: str, **kwargs: Any) -> str:
        config = get_config()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        if config.log_format == LogFormat.JSON:
            entry = {"timestamp": timestamp, "level": level, "logger": self.name, "message": message, **kwargs}
            return json.dumps(entry, default=str, ensure_ascii=False)

        # Text format with colors
        colors = {"DEBUG": "\033[36m", "INFO": "\033[32m", "WARNING": "\033[33m", "ERROR": "\033[31m", "CRITICAL": "\033[35m"}
        reset = "\033[0m"
        color = colors.get(level, "")

        parts = [f"{color}[{timestamp}] [{level:>8}]{reset} [{self.name}] {message}"]
        if kwargs:
            extras = " | ".join(f"{k}={v!r}" for k, v in kwargs.items())
            parts.append(f"  → {extras}")

        return "\n".join(parts)

    def _log(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        if self._should_log(level):
            print(self._format(level.value, message, **kwargs), file=sys.stderr)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log nível DEBUG."""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log nível INFO."""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log nível WARNING."""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log nível ERROR."""
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log nível CRITICAL."""
        self._log(LogLevel.CRITICAL, message, **kwargs)


def get_logger(name: str = "omniachain") -> OmniaLogger:
    """Retorna um logger com o nome especificado."""
    return OmniaLogger(name)
