# ReAct Agent

O **ReAct** (Reason + Act) segue um ciclo de raciocínio:

```
Thought → Action → Observation → Thought → ... → Answer
```

## Uso

```python
from omniachain import ReActAgent, Anthropic, web_search, calculator

agent = ReActAgent(
    provider=Anthropic(),
    tools=[web_search, calculator],
    name="researcher",
)

result = await agent.run("Qual a população do Brasil dividida por 27 estados?")
```

O agente irá:

1. **Thought**: "Preciso saber a população do Brasil"
2. **Action**: `web_search("população Brasil 2024")`
3. **Observation**: "~215 milhões"
4. **Thought**: "Agora divido por 27"
5. **Action**: `calculator("215000000 / 27")`
6. **Observation**: "~7.963.000"
7. **Answer**: "Aproximadamente 7,9 milhões por estado"

## Quando usar

- ✅ Pesquisa com múltiplas etapas
- ✅ Raciocínio que precisa de dados externos
- ✅ Cálculos baseados em informações dinâmicas
- ❌ Tarefas simples sem tools (use `Agent`)
