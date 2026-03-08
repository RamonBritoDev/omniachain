# Providers

Suporte nativo a **5 providers** de IA — mesma API para todos.

## Providers Disponíveis

| Provider | Classe | Modelos | Visão | Tools | STT | TTS | Image Gen |
|----------|--------|---------|:-----:|:-----:|:---:|:---:|:---------:|
| **Anthropic** | `Anthropic()` | Claude 3.5, 3, Haiku | ✅ | ✅ | ❌ | ❌ | ❌ |
| **OpenAI** | `OpenAI()` | GPT-4o, 4, 3.5 | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Groq** | `Groq()` | Llama 3, Mixtral | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Google** | `Google()` | Gemini Pro, Flash | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Ollama** | `Ollama()` | Qualquer local | ❌ | ❌ | ❌ | ❌ | ❌ |

## Uso

```python
from omniachain import Anthropic, OpenAI, Groq, Google, Ollama

# Todos seguem a mesma API!
provider = Anthropic("claude-3-5-sonnet-20241022")
provider = OpenAI("gpt-4o-mini")
provider = Groq("llama-3.1-70b-versatile")
provider = Google("gemini-pro")
provider = Ollama("llama3")

# Mesma chamada para qualquer provider
result = await provider.complete([Message.user("Olá!")])
```

## Provider Pool

Gerencia múltiplos providers com estratégias automáticas:

```python
from omniachain import ProviderPool

pool = ProviderPool()
pool.add(Anthropic())
pool.add(OpenAI())
pool.add(Groq())

# Estratégias
provider = await pool.get(strategy="fallback")      # Tenta em ordem
provider = await pool.get(strategy="round_robin")    # Alterna
provider = await pool.get(strategy="cheapest")       # Mais barato
provider = await pool.get(strategy="fastest")        # Mais rápido
```

## Custos

| Modelo | Input/1K | Output/1K |
|--------|----------|-----------|
| claude-3-5-sonnet | $0.003 | $0.015 |
| gpt-4o | $0.005 | $0.015 |
| gpt-4o-mini | $0.00015 | $0.0006 |
| llama-3.1 (Groq) | $0.00059 | $0.00079 |
| gemini-pro | $0.00025 | $0.0005 |
| Ollama | **Grátis** | **Grátis** |
