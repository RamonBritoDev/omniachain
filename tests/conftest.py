"""conftest.py — Configuração global dos testes."""

import pytest


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config entre testes."""
    from omniachain.core.config import reset_config
    reset_config()
    yield
    reset_config()
