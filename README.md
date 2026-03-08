# 🔗 OmniaChain

**Framework Python para agentes de IA — async-first, multi-modal, MCP nativo.**

> Mais poderoso que LangChain. Mais simples que CrewAI. Seguro com PGP.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ Recursos

| Recurso | Descrição |
|---------|-----------|
| 🚀 **Async-first** | `asyncio` em tudo — zero bloqueio |
| 🎨 **Multi-modal** | Texto, PDF, imagem, áudio, vídeo, CSV, URL, código |
| 🤖 **5 Providers** | Anthropic, OpenAI, Groq, Ollama, Google Gemini |
| 🛠️ **Tools nativas** | Web search, calculator, HTTP, file, code exec, browser |
| 🧠 **4 tipos de memória** | Buffer, Summary, Vector (pgvector), Persistent (SQLite) |
| 🔌 **MCP nativo** | Server + Client + Memory Server via MCP Protocol |
| 🔐 **Segurança PGP** | Keypair, permissions, guard, middleware com auditoria |
| 🎭 **4 tipos de agente** | ReAct, Multimodal, Planner, Supervisor |
| 📊 **Observability** | Logger, Tracer, Cost Tracker, Dashboard |
| 🔄 **Pipelines** | Sequencial, Paralelo, Condicional, Router |
| 🎯 **Orquestração** | Session multi-agente, Pool de providers, Fallback |

---

## 🚀 Instalação

```bash
pip install omniachain

# Com todos os extras
pip install omniachain[all]

# Extras específicos
pip install omniachain[vector]    # pgvector
pip install omniachain[browser]   # Playwright
pip install omniachain[audio]     # Whisper
```

---

## 📖 Uso Rápido

### Agente básico (3 linhas!)

```python
from omniachain import Agent, Anthropic, calculator, web_search

agent = Agent(provider=Anthropic(), tools=[calculator, web_search])
result = await agent.run("Quanto é 15 * 32 + raiz de 144?")
print(result.content)  # "O resultado é 492"
```

### Multi-modal

```python
from omniachain import MultimodalAgent, OpenAI

agent = MultimodalAgent(provider=OpenAI("gpt-4o"))
result = await agent.run(
    "Analise estes dados",
    inputs=["relatorio.pdf", "grafico.png", "dados.csv"]
)
```

### Multi-agente com Supervisor

```python
from omniachain import Anthropic, Groq, ReActAgent, SupervisorAgent, web_search, calculator

researcher = ReActAgent(provider=Anthropic(), tools=[web_search], name="researcher")
analyst = ReActAgent(provider=Groq(), tools=[calculator], name="analyst")

supervisor = SupervisorAgent(
    provider=Anthropic(),
    sub_agents=[researcher, analyst],
)
result = await supervisor.run("Pesquise IA e analise os dados")
```

### MCP Server

```python
from omniachain import MCPServer

server = MCPServer("meu-servidor")

@server.tool
async def consultar(query: str) -> str:
    """Consulta dados."""
    return f"Resultado: {query}"

await server.run(transport="stdio")
```

### Segurança PGP

```python
from omniachain import Agent, KeyPair, Permissions

keys = await KeyPair.generate(agent_name="admin")
perms = Permissions()
perms.grant(keys.fingerprint, tools=["calculator"])  # Só calculator
perms.deny(keys.fingerprint, tools=["code_exec"])    # Nunca code_exec

agent = Agent(provider=..., tools=[...], keypair=keys, permissions=perms)
```

### Custom Tool

```python
from omniachain import tool

@tool(cache=True, retries=3)
async def buscar_preco(produto: str, moeda: str = "BRL") -> float:
    """Busca o preço de um produto."""
    return 42.0

# Schema JSON gerado automaticamente!
print(buscar_preco.schema)
```

---

## 🏗️ Arquitetura

```
omniachain/
├── core/           # Config, Message, Response, Context, Chain, Errors
├── providers/      # Anthropic, OpenAI, Groq, Ollama, Google
├── loaders/        # Auto-detect: PDF, Image, Audio, Video, CSV, URL, Code
├── tools/          # @tool decorator, calculator, HTTP, file, code, search
├── memory/         # Buffer, Summary, Vector (pgvector), Persistent, MCP
├── mcp/            # Server, Client, Transport (stdio/HTTP), Registry
├── security/       # KeyPair (PGP), Permissions, Guard, Middleware
├── agents/         # Base, ReAct, Multimodal, Planner, Supervisor
├── pipeline/       # Sequential, Parallel, Conditional, Router
├── orchestration/  # Session, ProviderPool, Fallback, CostOptimizer
└── observability/  # Logger, Tracer, CostTracker, Dashboard
```

---

## 🔐 Segurança

O OmniaChain implementa segurança PGP completa:

1. **KeyPair**: Cada agente tem par de chaves (GPG real ou HMAC fallback)
2. **Permissions**: Grant/Deny por tool, memory e provider
3. **Guard**: Decorator `@requires_permission` para proteger funções
4. **Middleware**: Valida assinatura + permissão + anti-replay + auditoria

---

## 🧠 Memória Vetorial (MCP + pgvector)

```python
from omniachain.memory.mcp_memory import MCPMemoryServer

# Servidor MCP de memória vetorial
server = MCPMemoryServer(dsn="postgresql://localhost/omniachain")
await server.run(transport="stdio")

# Qualquer agente MCP pode acessar:
# - memory_store: armazena com embedding
# - memory_search: busca semântica
# - memory_delete: remove por ID
```

---

## 📊 Observabilidade

```python
from omniachain import CostTracker, Tracer

tracker = CostTracker()
tracker.record(response)

print(f"Custo total: ${tracker.total_cost:.4f}")
print(tracker.summary())
```

---

## 🧪 Testes

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## 📁 Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `ANTHROPIC_API_KEY` | API key Anthropic |
| `OPENAI_API_KEY` | API key OpenAI |
| `GROQ_API_KEY` | API key Groq |
| `GOOGLE_API_KEY` | API key Google |
| `OMNIA_DEFAULT_PROVIDER` | Provider padrão |
| `OMNIA_PGVECTOR_DSN` | DSN PostgreSQL pgvector |
| `OMNIA_SECURITY_ENABLED` | Ativar segurança PGP |

---

## 📜 Licença

MIT License — Use como quiser.

---

**Feito com ❤️ para a comunidade de IA.**
