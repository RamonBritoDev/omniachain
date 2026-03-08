"""Testes — Memory: buffer e persistent."""

import pytest
import asyncio
import os
import tempfile
from omniachain.memory.buffer import BufferMemory
from omniachain.memory.summary import SummaryMemory
from omniachain.memory.persistent import PersistentMemory
from omniachain.core.message import Message


class TestBufferMemory:
    @pytest.mark.asyncio
    async def test_add_and_get(self):
        mem = BufferMemory()
        await mem.add(Message.user("Olá"))
        await mem.add(Message.assistant("Oi!"))
        msgs = await mem.get_messages()
        assert len(msgs) == 2

    @pytest.mark.asyncio
    async def test_max_messages(self):
        mem = BufferMemory(max_messages=5)
        for i in range(10):
            await mem.add(Message.user(f"msg {i}"))
        msgs = await mem.get_messages()
        assert len(msgs) <= 5

    @pytest.mark.asyncio
    async def test_search(self):
        mem = BufferMemory()
        await mem.add(Message.user("Python é legal"))
        await mem.add(Message.user("Java é bom"))
        results = await mem.search("Python")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        mem = BufferMemory()
        await mem.add(Message.user("teste"))
        await mem.clear()
        assert mem.size == 0


class TestSummaryMemory:
    @pytest.mark.asyncio
    async def test_basic(self):
        mem = SummaryMemory(max_messages=5)
        for i in range(3):
            await mem.add(Message.user(f"msg {i}"))
        msgs = await mem.get_messages()
        assert len(msgs) >= 3

    @pytest.mark.asyncio
    async def test_auto_summary(self):
        mem = SummaryMemory(max_messages=4)
        for i in range(6):
            await mem.add(Message.user(f"mensagem {i}"))
        assert mem.summary_count >= 1


class TestPersistentMemory:
    @pytest.mark.asyncio
    async def test_persist_and_load(self):
        db_path = os.path.join(tempfile.gettempdir(), "omniachain_test_memory.db")
        # Clean up from previous runs
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except OSError:
                pass
        try:
            mem = PersistentMemory(db_path)
            await mem.initialize()
            await mem.add(Message.user("persistente"))
            msgs = await mem.get_messages()
            assert len(msgs) == 1
            assert msgs[0].text == "persistente"
            await mem.close()
        finally:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except OSError:
                pass

    @pytest.mark.asyncio
    async def test_kv_store(self):
        db_path = os.path.join(tempfile.gettempdir(), "omniachain_test_kv.db")
        try:
            mem = PersistentMemory(db_path)
            await mem.initialize()
            await mem.set("chave", {"valor": 42})
            result = await mem.get("chave")
            assert result == {"valor": 42}
            await mem.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
