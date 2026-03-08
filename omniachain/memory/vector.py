"""
OmniaChain — VectorMemory: busca semântica com pgvector.

Usa PostgreSQL + extensão pgvector como backend principal.
Fallback para busca em memória quando pgvector não está disponível.

Exemplo::

    memory = VectorMemory(dsn="postgresql://user:pass@localhost/db")
    await memory.store("Brasília é a capital do Brasil", metadata={"source": "wiki"})
    results = await memory.search("capital brasileira", limit=3)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Optional

from omniachain.core.errors import MemoryError
from omniachain.core.message import Message


class VectorMemory:
    """Memória vetorial com busca semântica usando pgvector.

    Armazena textos com embeddings vetoriais e busca por similaridade.
    Suporta pgvector (PostgreSQL) como backend principal e fallback em memória.

    Exemplo::

        memory = VectorMemory(dsn="postgresql://localhost/omniachain")
        await memory.initialize()
        await memory.store("Python é uma linguagem de programação")
        results = await memory.search("linguagem de programação", limit=5)
    """

    def __init__(
        self,
        dsn: Optional[str] = None,
        table_name: str = "omniachain_memories",
        embedding_provider: Optional[Any] = None,
        embedding_dim: int = 1536,
    ) -> None:
        self.dsn = dsn
        self.table_name = table_name
        self.embedding_provider = embedding_provider
        self.embedding_dim = embedding_dim
        self._pool: Optional[Any] = None
        self._initialized = False

        # Fallback in-memory store
        self._memory_store: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Inicializa conexão com pgvector ou fallback."""
        if self.dsn:
            await self._init_pgvector()
        self._initialized = True

    async def _init_pgvector(self) -> None:
        """Inicializa PostgreSQL + pgvector."""
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)

            async with self._pool.acquire() as conn:
                # Criar extensão e tabela
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector({self.embedding_dim}),
                        metadata JSONB DEFAULT '{{}}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                # Criar index para busca por similaridade
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding
                    ON {self.table_name}
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)

        except ImportError:
            raise MemoryError(
                "Pacote 'asyncpg' não instalado.",
                memory_type="vector",
                suggestion="Instale com: pip install asyncpg pgvector",
            )
        except Exception as e:
            # Fallback para in-memory
            self._pool = None
            import warnings
            warnings.warn(
                f"pgvector indisponível ({e}), usando fallback em memória.",
                stacklevel=2,
            )

    async def _get_embedding(self, text: str) -> list[float]:
        """Gera embedding de um texto."""
        if self.embedding_provider:
            return await self.embedding_provider.embed(text)

        # Fallback: hash-based pseudo-embedding (para desenvolvimento)
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        # Expandir para embedding_dim floats entre -1 e 1
        embedding = []
        for i in range(self.embedding_dim):
            byte_idx = i % len(h)
            embedding.append((h[byte_idx] / 128.0) - 1.0)
        return embedding

    async def store(
        self,
        content: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
        id: Optional[str] = None,
    ) -> str:
        """Armazena conteúdo com embedding vetorial.

        Args:
            content: Texto para armazenar.
            metadata: Metadados associados.
            id: ID customizado. Se None, gera automaticamente.

        Returns:
            ID do registro armazenado.
        """
        if not self._initialized:
            await self.initialize()

        doc_id = id or uuid.uuid4().hex[:16]
        embedding = await self._get_embedding(content)
        meta = metadata or {}

        if self._pool:
            await self._store_pgvector(doc_id, content, embedding, meta)
        else:
            self._memory_store.append({
                "id": doc_id,
                "content": content,
                "embedding": embedding,
                "metadata": meta,
            })

        return doc_id

    async def _store_pgvector(
        self, doc_id: str, content: str, embedding: list[float], metadata: dict
    ) -> None:
        """Armazena no pgvector."""
        async with self._pool.acquire() as conn:
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} (id, content, embedding, metadata)
                VALUES ($1, $2, $3::vector, $4::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata;
                """,
                doc_id, content, embedding_str, json.dumps(metadata),
            )

    async def search(
        self,
        query: str,
        limit: int = 5,
        metadata_filter: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Busca semântica por similaridade.

        Args:
            query: Texto de busca.
            limit: Número máximo de resultados.
            metadata_filter: Filtro de metadados.

        Returns:
            Lista de docs com content, metadata e score.
        """
        if not self._initialized:
            await self.initialize()

        query_embedding = await self._get_embedding(query)

        if self._pool:
            return await self._search_pgvector(query_embedding, limit, metadata_filter)
        else:
            return self._search_memory(query_embedding, limit, metadata_filter)

    async def _search_pgvector(
        self, embedding: list[float], limit: int, metadata_filter: Optional[dict]
    ) -> list[dict[str, Any]]:
        """Busca por similaridade no pgvector."""
        async with self._pool.acquire() as conn:
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            query = f"""
                SELECT id, content, metadata,
                       1 - (embedding <=> $1::vector) as similarity
                FROM {self.table_name}
                ORDER BY embedding <=> $1::vector
                LIMIT $2;
            """
            rows = await conn.fetch(query, embedding_str, limit)

            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "score": float(row["similarity"]),
                })
            return results

    def _search_memory(
        self, embedding: list[float], limit: int, metadata_filter: Optional[dict]
    ) -> list[dict[str, Any]]:
        """Busca por similaridade em memória (fallback)."""
        import math

        scored = []
        for doc in self._memory_store:
            # Cosine similarity
            dot = sum(a * b for a, b in zip(embedding, doc["embedding"]))
            norm_a = math.sqrt(sum(a * a for a in embedding))
            norm_b = math.sqrt(sum(b * b for b in doc["embedding"]))
            similarity = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

            if metadata_filter:
                match = all(doc["metadata"].get(k) == v for k, v in metadata_filter.items())
                if not match:
                    continue

            scored.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": similarity,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    async def delete(self, doc_id: str) -> bool:
        """Remove um documento por ID."""
        if self._pool:
            async with self._pool.acquire() as conn:
                result = await conn.execute(
                    f"DELETE FROM {self.table_name} WHERE id = $1;", doc_id
                )
                return "DELETE 1" in result
        else:
            before = len(self._memory_store)
            self._memory_store = [d for d in self._memory_store if d["id"] != doc_id]
            return len(self._memory_store) < before

    async def clear(self) -> None:
        """Remove todos os documentos."""
        if self._pool:
            async with self._pool.acquire() as conn:
                await conn.execute(f"DELETE FROM {self.table_name};")
        self._memory_store.clear()

    async def close(self) -> None:
        """Fecha conexões."""
        if self._pool:
            await self._pool.close()

    @property
    def count(self) -> int:
        """Número de documentos armazenados (in-memory only)."""
        return len(self._memory_store)
