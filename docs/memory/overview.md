# Memória

O OmniaChain oferece **4 tipos de memória** para diferentes necessidades.

## Comparação

| Tipo | Persistente | Semântica | Resumo | Melhor para |
|------|:-----------:|:---------:|:------:|-------------|
| `BufferMemory` | ❌ | ❌ | ❌ | Chat simples |
| `SummaryMemory` | ❌ | ❌ | ✅ | Conversas longas |
| `PersistentMemory` | ✅ | ❌ | ❌ | Dados duráveis |
| `VectorMemory` | ✅ | ✅ | ❌ | Busca inteligente |

## BufferMemory

Mantém as últimas N mensagens em RAM:

```python
from omniachain import Agent, OpenAI, BufferMemory

agent = Agent(
    provider=OpenAI(),
    memory=BufferMemory(max_messages=50),
)
```

## SummaryMemory

Resume automaticamente mensagens antigas usando o LLM:

```python
from omniachain import SummaryMemory

memory = SummaryMemory(max_messages=20)
# Quando passa de 20, as mais antigas viram resumo
```

## PersistentMemory

Persiste em **SQLite** — sobrevive a reinícios:

```python
from omniachain import PersistentMemory

memory = PersistentMemory("meu_agente.db")
await memory.initialize()

# Key-value store
await memory.set("preferencias", {"tema": "dark"})
dados = await memory.get("preferencias")
```

## VectorMemory

Busca **semântica** com pgvector (PostgreSQL):

```python
from omniachain import VectorMemory

memory = VectorMemory(dsn="postgresql://localhost/omniachain")
await memory.initialize()

# Armazenar com embedding
await memory.store("Python é ótimo para IA", metadata={"topic": "tech"})

# Busca semântica
results = await memory.search("linguagem de programação", limit=5)
```

!!! info "Fallback"
    Sem PostgreSQL? VectorMemory usa um índice **in-memory** automaticamente.

## MCP Memory Server

Expõe a memória vetorial via MCP para outros agentes:

```python
from omniachain.memory.mcp_memory import MCPMemoryServer

server = MCPMemoryServer(dsn="postgresql://localhost/omniachain")
await server.run(transport="stdio")

# Tools expostas via MCP:
# - memory_store: armazena com embedding
# - memory_search: busca semântica
# - memory_delete: remove por ID
```
