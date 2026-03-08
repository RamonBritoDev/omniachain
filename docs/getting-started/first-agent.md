# Primeiro Agente

Crie seu primeiro agente de IA em **3 linhas**.

## Agente Básico

```python
import asyncio
from omniachain import Agent, OpenAI, calculator

async def main():
    agent = Agent(
        provider=OpenAI("gpt-4o-mini"),
        tools=[calculator],
    )

    result = await agent.run("Quanto é 2^10 + 42?")
    print(result.content)    # "1066"
    print(result.usage.cost) # $0.000015

asyncio.run(main())
```

!!! note "Resultado"
    O agente **decide sozinho** quando usar o calculator — esse é o poder do tool calling!

---

## Agente com Web Search

```python
from omniachain import Agent, Anthropic, web_search, calculator

agent = Agent(
    provider=Anthropic(),
    tools=[web_search, calculator],
    system_prompt="Você é um pesquisador. Responda em português.",
)

result = await agent.run("Qual a população do Brasil e quanto é dividido por 27?")
```

O agente irá:
1. Usar `web_search` para encontrar a população
2. Usar `calculator` para dividir por 27
3. Combinar e responder

---

## Streaming

```python
async for token in agent.stream("Conte uma história curta"):
    print(token, end="", flush=True)
```

---

## Memória

O agente **lembra** conversas anteriores automaticamente:

```python
agent = Agent(provider=OpenAI(), memory="buffer")

await agent.run("Meu nome é João")
result = await agent.run("Qual é meu nome?")
print(result.content)  # "Seu nome é João"
```

Tipos de memória:

| Tipo | Uso |
|------|-----|
| `"buffer"` | Últimas N mensagens em RAM |
| `"summary"` | Resume mensagens antigas com LLM |
| `BufferMemory()` | Configuração manual |
| `PersistentMemory("db.sqlite")` | Persiste em disco |

---

## Custo e Tokens

```python
result = await agent.run("Explique IA")

print(f"Tokens: {result.usage.total_tokens}")
print(f"Custo:  ${result.usage.cost:.4f}")
print(f"Modelo: {result.model}")
```

---

!!! tip "Próximos passos"
    - [Criar suas próprias tools](../tools/creating-tools.md)
    - [Agentes especializados](../agents/overview.md) (ReAct, Planner, Supervisor)
    - [Segurança PGP](../security/pgp.md) para controle de acesso
