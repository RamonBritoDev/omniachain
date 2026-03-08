"""Testes — Tools: decorator @tool, calculator, schema."""

import pytest
import asyncio
from omniachain.tools.base import tool, Tool


@tool
async def soma(a: int, b: int) -> int:
    """Soma dois números."""
    return a + b


@tool(cache=True, retries=2)
async def multiplica(x: float, y: float) -> float:
    """Multiplica dois números."""
    return x * y


class TestToolDecorator:
    def test_tool_name(self):
        assert soma.name == "soma"

    def test_tool_description(self):
        assert "Soma dois números" in soma.description

    def test_tool_schema(self):
        assert "properties" in soma.schema
        assert "a" in soma.schema["properties"]
        assert "b" in soma.schema["properties"]
        assert soma.schema["properties"]["a"]["type"] == "integer"

    def test_openai_schema(self):
        s = soma.to_openai_schema()
        assert s["type"] == "function"
        assert s["function"]["name"] == "soma"

    def test_anthropic_schema(self):
        s = soma.to_anthropic_schema()
        assert s["name"] == "soma"
        assert s["input_schema"]["type"] == "object"


class TestToolExecution:
    @pytest.mark.asyncio
    async def test_execute(self):
        result = await soma.execute(a=3, b=4)
        assert result.success is True
        assert result.result == 7

    @pytest.mark.asyncio
    async def test_cached(self):
        result1 = await multiplica.execute(x=2.0, y=3.0)
        result2 = await multiplica.execute(x=2.0, y=3.0)
        assert result1.result == 6.0
        assert result2.cached is True

    @pytest.mark.asyncio
    async def test_call_direct(self):
        result = await soma(a=10, b=20)
        assert result == 30


class TestCalculator:
    @pytest.mark.asyncio
    async def test_basic(self):
        from omniachain.tools.calculator import calculator
        result = await calculator.execute(expression="2 + 3")
        assert result.success
        assert "5" in str(result.result)

    @pytest.mark.asyncio
    async def test_sqrt(self):
        from omniachain.tools.calculator import calculator
        result = await calculator.execute(expression="sqrt(144)")
        assert result.success
        assert "12" in str(result.result)
