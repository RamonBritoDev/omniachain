# Configuração

## OmniaConfig

A configuração global é gerenciada pela classe `OmniaConfig`:

```python
from omniachain import get_config

config = get_config()
print(config.default_provider)   # "anthropic"
print(config.default_timeout)    # 30.0
print(config.security_enabled)   # False
```

## Todas as Variáveis

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OMNIA_DEFAULT_PROVIDER` | `anthropic` | Provider padrão |
| `OMNIA_DEFAULT_MODEL` | `claude-3-5-sonnet-20241022` | Modelo padrão |
| `OMNIA_DEFAULT_TIMEOUT` | `30.0` | Timeout em segundos |
| `OMNIA_MAX_RETRIES` | `3` | Máximo de retries |
| `OMNIA_MAX_CONCURRENT` | `10` | Máximo de chamadas paralelas |
| `OMNIA_PGVECTOR_DSN` | — | DSN do PostgreSQL para pgvector |
| `OMNIA_MEMORY_BACKEND` | `buffer` | Backend de memória padrão |
| `OMNIA_SECURITY_ENABLED` | `false` | Ativa segurança PGP |
| `OMNIA_GPG_HOME` | `~/.gnupg` | Diretório GPG |
| `OMNIA_LOG_LEVEL` | `INFO` | Nível de log |
| `OMNIA_LOG_FORMAT` | `text` | Formato: `text` ou `json` |
| `OMNIA_TRACE_ENABLED` | `false` | Ativa tracing |
| `OMNIA_COST_TRACKING` | `true` | Ativa tracking de custos |

## API Keys

| Provider | Variável |
|----------|----------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` |
| OpenAI (GPT) | `OPENAI_API_KEY` |
| Groq (Llama) | `GROQ_API_KEY` |
| Google (Gemini) | `GOOGLE_API_KEY` |
| Ollama (local) | `OLLAMA_BASE_URL` (padrão: `http://localhost:11434`) |
