# Observability

Logger, Tracer, Cost Tracker e Dashboard — tudo built-in.

## Cost Tracker

Rastreamento de custos em **tempo real**:

```python
from omniachain import CostTracker

tracker = CostTracker()

# Registra automaticamente
tracker.record(response)

# Métricas
print(f"Custo total:  ${tracker.total_cost:.4f}")
print(f"Total tokens: {tracker.total_tokens:,}")

# Por provider
for prov, data in tracker.by_provider().items():
    print(f"  {prov}: ${data['cost']:.4f} ({data['calls']} chamadas)")

# Resumo
print(tracker.summary())
```

## Logger

Logger estruturado com cores e formato JSON:

```python
from omniachain import get_logger

logger = get_logger("meu-agente")

logger.info("Agente iniciado", model="gpt-4o")
logger.warning("Rate limit próximo", remaining=5)
logger.error("Falha na API", provider="openai", error="timeout")
```

Saída (texto):
```
[2025-01-15 14:30:22] [    INFO] [meu-agente] Agente iniciado
  → model='gpt-4o'
```

Saída (JSON, via `OMNIA_LOG_FORMAT=json`):
```json
{"timestamp": "2025-01-15 14:30:22", "level": "INFO", "logger": "meu-agente", "message": "Agente iniciado", "model": "gpt-4o"}
```

## Tracer

Trace completo de cada execução:

```python
from omniachain import Tracer

tracer = Tracer()
tracer.start_trace(metadata={"task": "pesquisa"})

with tracer.span("llm_call") as span:
    result = await provider.complete(messages)
    span.attributes["model"] = result.model
    span.attributes["tokens"] = result.usage.total_tokens

with tracer.span("tool_exec") as span:
    await calculator.execute(expression="2+2")
    span.attributes["tool"] = "calculator"

# Exportar
traces = tracer.export_json()
```

## Dashboard

Dashboard visual no terminal:

```python
from omniachain.observability.dashboard import Dashboard

dashboard = Dashboard(cost_tracker=tracker, tracer=tracer)
dashboard.show()
```

Exibe com Rich:
- 💰 Painel de custos
- 🔍 Tabela de traces recentes
- 📊 Custos por provider
