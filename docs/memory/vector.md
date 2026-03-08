# Memória Vetorial (pgvector)

Busca semântica usando **pgvector** com PostgreSQL — encontre informações por **significado**, não por palavras-chave.

## Setup

```bash
# PostgreSQL com pgvector
docker run -d -p 5432:5432 \
  -e POSTGRES_PASSWORD=pass \
  ankane/pgvector

pip install omniachain[vector]
```

```bash
export OMNIA_PGVECTOR_DSN="postgresql://postgres:pass@localhost/omniachain"
```

## Uso

```python
from omniachain import VectorMemory

memory = VectorMemory()  # Usa OMNIA_PGVECTOR_DSN
await memory.initialize()

# Armazenar
await memory.store(
    "Python é a melhor linguagem para IA e machine learning",
    metadata={"topic": "tech", "author": "admin"},
)

await memory.store(
    "O Brasil tem 215 milhões de habitantes",
    metadata={"topic": "geo"},
)

# Busca semântica
results = await memory.search("linguagem de programação", limit=3)
for r in results:
    print(f"Score: {r['score']:.2f} | {r['content'][:50]}")
```

## Como funciona

```mermaid
graph LR
    A[Texto] --> B[Embedding Model]
    B --> C[Vetor 1536D]
    C --> D[pgvector INSERT]
    E[Query] --> F[Embedding Model]
    F --> G[Vetor 1536D]
    G --> H[pgvector: cosine similarity]
    D --> H
    H --> I[Top-K resultados]
```

## MCP Memory Server

Exponha a memória vetorial para **qualquer agente MCP**:

```python
from omniachain.memory.mcp_memory import MCPMemoryServer

server = MCPMemoryServer(
    dsn="postgresql://localhost/omniachain",
    name="memory-server",
)
await server.run(transport="stdio")
```

Outros agentes podem chamar:
- `memory_store(content, namespace, metadata)`
- `memory_search(query, limit, namespace)`
- `memory_delete(id)`
