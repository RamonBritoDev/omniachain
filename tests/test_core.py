"""Testes — Core: config, message, response, context, errors."""

import pytest
import asyncio
from omniachain.core.config import OmniaConfig, get_config, reset_config
from omniachain.core.message import Message, ContentType
from omniachain.core.response import Response, Usage
from omniachain.core.context import Context
from omniachain.core.errors import OmniaError, ProviderError, ToolError


class TestConfig:
    def test_config_defaults(self):
        reset_config()
        config = get_config()
        assert config.default_provider == "anthropic"
        assert config.default_timeout == 30.0
        assert config.max_retries == 3

    def test_config_singleton(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_config_reset(self):
        c1 = get_config()
        reset_config()
        c2 = get_config()
        assert c1 is not c2


class TestMessage:
    def test_user_message(self):
        msg = Message.user("Olá, mundo!")
        assert msg.role.value == "user"
        assert msg.text == "Olá, mundo!"

    def test_assistant_message(self):
        msg = Message.assistant("Resposta")
        assert msg.role.value == "assistant"
        assert msg.text == "Resposta"

    def test_system_message(self):
        msg = Message.system("Você é um assistente")
        assert msg.role.value == "system"
        assert len(msg.content) == 1
        assert msg.content[0].type == ContentType.TEXT

    def test_multimodal_message(self):
        from omniachain.core.message import MessageContent
        msg = Message.user("Descreva", MessageContent.image("https://example.com/img.png"))
        assert len(msg.content) >= 2


class TestResponse:
    def test_response_basic(self):
        r = Response(content="Resultado", provider="anthropic", model="claude-3")
        assert r.content == "Resultado"
        assert r.provider == "anthropic"

    def test_usage(self):
        u = Usage(input_tokens=100, output_tokens=50, total_tokens=150)
        assert u.total_tokens == 150

    def test_usage_add(self):
        u1 = Usage(input_tokens=100, output_tokens=50)
        u2 = Usage(input_tokens=200, output_tokens=100)
        u3 = u1 + u2
        assert u3.input_tokens == 300
        assert u3.output_tokens == 150


class TestContext:
    def test_context_variables(self):
        ctx = Context()
        ctx.set("key", "value")
        assert ctx.get("key") == "value"

    def test_context_fork(self):
        ctx = Context()
        ctx.set("x", 1)
        fork = ctx.fork()
        fork.set("y", 2)
        assert ctx.get("y") is None
        assert fork.get("x") == 1

    def test_context_messages(self):
        ctx = Context()
        msg = Message.user("test")
        ctx.add_message(msg)
        assert len(ctx.messages) == 1


class TestErrors:
    def test_omnia_error(self):
        err = OmniaError("algo deu errado", suggestion="tente X")
        assert "algo deu errado" in str(err)

    def test_provider_error(self):
        err = ProviderError("API down", provider="openai")
        assert "API down" in str(err)

    def test_tool_error(self):
        err = ToolError("timeout", tool_name="web_search")
        assert "timeout" in str(err)
