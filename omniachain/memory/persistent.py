"""
OmniaChain — PersistentMemory: persiste em SQLite.

Exemplo::

    memory = PersistentMemory("agent_memory.db")
    await memory.add(Message.user("Olá"))
    msgs = await memory.get_messages()
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from omniachain.core.message import Message, MessageContent, ContentType, Role


class PersistentMemory:
    """Memória persistente em disco usando SQLite.

    Exemplo::

        memory = PersistentMemory("my_agent.db")
        await memory.initialize()
        await memory.add(Message.user("Olá!"))
    """

    def __init__(self, db_path: str = "omniachain_memory.db") -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    async def initialize(self) -> None:
        """Cria a tabela se não existir."""
        import asyncio
        await asyncio.to_thread(self._init_db)

    def _init_db(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                trace_id TEXT,
                metadata TEXT DEFAULT '{}'
            );
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        self._conn.commit()

    async def add(self, message: Message) -> None:
        """Persiste uma mensagem no SQLite."""
        import asyncio

        if not self._conn:
            await self.initialize()

        content_data = json.dumps([
            {"type": c.type.value, "data": str(c.data), "mime_type": c.mime_type, "metadata": c.metadata}
            for c in message.content
        ], ensure_ascii=False)

        await asyncio.to_thread(
            self._insert_message,
            uuid.uuid4().hex[:16],
            message.role.value,
            content_data,
            message.timestamp.isoformat(),
            message.trace_id or "",
            json.dumps(message.metadata),
        )

    def _insert_message(self, id: str, role: str, content: str, timestamp: str, trace_id: str, metadata: str) -> None:
        assert self._conn
        self._conn.execute(
            "INSERT INTO messages (id, role, content, timestamp, trace_id, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (id, role, content, timestamp, trace_id, metadata),
        )
        self._conn.commit()

    async def get_messages(self, limit: Optional[int] = None) -> list[Message]:
        """Carrega mensagens do SQLite."""
        import asyncio

        if not self._conn:
            await self.initialize()

        rows = await asyncio.to_thread(self._fetch_messages, limit)

        messages = []
        for row in rows:
            _, role, content_json, timestamp, trace_id, metadata = row
            content_list = json.loads(content_json)

            contents = []
            for c in content_list:
                contents.append(MessageContent(
                    type=ContentType(c["type"]),
                    data=c["data"],
                    mime_type=c.get("mime_type"),
                    metadata=c.get("metadata", {}),
                ))

            messages.append(Message(
                role=Role(role),
                content=contents,
                timestamp=datetime.fromisoformat(timestamp),
                trace_id=trace_id or None,
                metadata=json.loads(metadata) if metadata else {},
            ))

        return messages

    def _fetch_messages(self, limit: Optional[int]) -> list:
        assert self._conn
        query = "SELECT * FROM messages ORDER BY timestamp ASC"
        if limit:
            query += f" LIMIT {limit}"
        return self._conn.execute(query).fetchall()

    async def set(self, key: str, value: Any) -> None:
        """Armazena um valor no key-value store."""
        import asyncio

        if not self._conn:
            await self.initialize()

        await asyncio.to_thread(self._set_kv, key, json.dumps(value, default=str), datetime.now(timezone.utc).isoformat())

    def _set_kv(self, key: str, value: str, ts: str) -> None:
        assert self._conn
        self._conn.execute(
            "INSERT OR REPLACE INTO kv_store (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, ts),
        )
        self._conn.commit()

    async def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor do key-value store."""
        import asyncio

        if not self._conn:
            await self.initialize()

        result = await asyncio.to_thread(self._get_kv, key)
        if result:
            return json.loads(result[0])
        return default

    def _get_kv(self, key: str) -> Optional[tuple]:
        assert self._conn
        return self._conn.execute("SELECT value FROM kv_store WHERE key = ?", (key,)).fetchone()

    async def clear(self) -> None:
        """Limpa todas as mensagens e dados."""
        import asyncio
        if self._conn:
            await asyncio.to_thread(self._clear_all)

    def _clear_all(self) -> None:
        assert self._conn
        self._conn.execute("DELETE FROM messages")
        self._conn.execute("DELETE FROM kv_store")
        self._conn.commit()

    async def search(self, query: str, limit: int = 5) -> list[Message]:
        """Busca mensagens por texto (LIKE)."""
        import asyncio
        if not self._conn:
            await self.initialize()

        rows = await asyncio.to_thread(self._search_messages, query, limit)
        messages = []
        for row in rows:
            _, role, content_json, timestamp, trace_id, metadata = row
            content_list = json.loads(content_json)
            contents = [
                MessageContent(type=ContentType(c["type"]), data=c["data"], mime_type=c.get("mime_type"), metadata=c.get("metadata", {}))
                for c in content_list
            ]
            messages.append(Message(role=Role(role), content=contents, timestamp=datetime.fromisoformat(timestamp), trace_id=trace_id or None))
        return messages

    def _search_messages(self, query: str, limit: int) -> list:
        assert self._conn
        return self._conn.execute(
            "SELECT * FROM messages WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()

    async def close(self) -> None:
        """Fecha conexão com SQLite."""
        import asyncio
        if self._conn:
            conn = self._conn
            self._conn = None
            await asyncio.to_thread(conn.close)
