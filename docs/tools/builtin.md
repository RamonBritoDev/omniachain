# Tools Nativas

Tools incluídas no OmniaChain, prontas para usar.

## Calculator

```python
from omniachain import calculator

result = await calculator.execute(expression="sqrt(144) + 2^10")
# → 1036.0
```

Suporta: `+`, `-`, `*`, `/`, `**`, `sqrt`, `sin`, `cos`, `abs`, `log`, `pi`, `e`

## Web Search

```python
from omniachain import web_search

result = await web_search.execute(query="Python 3.12 novidades", num_results=5)
```

Usa DuckDuckGo (sem API key). Retorna título + snippet dos resultados.

## HTTP Request

```python
from omniachain import http_request

result = await http_request.execute(
    url="https://api.github.com/repos/python/cpython",
    method="GET",
)
```

Suporta todos os métodos HTTP com retry automático.

## File Read/Write

```python
from omniachain import file_read, file_write

# Ler
content = await file_read.execute(path="dados.txt")

# Escrever
await file_write.execute(path="output.txt", content="Resultado...")
```

## Code Exec

```python
from omniachain import code_exec

result = await code_exec.execute(code="print(sum(range(100)))")
# → "4950"
```

!!! warning "Segurança"
    Executa em subprocess com timeout. Para produção, use com `Permissions` para controlar acesso.

## Browser Navigate

```python
from omniachain.tools.browser import browser_navigate

result = await browser_navigate.execute(
    url="https://example.com",
    action="read",  # ou "screenshot"
)
```

!!! note "Requisito"
    Precisa de Playwright: `pip install omniachain[browser] && playwright install chromium`

## Speech-to-Text

```python
from omniachain import speech_to_text

result = await speech_to_text.execute(
    file_path="audio.mp3",
    language="pt",
    backend="auto",
)
```

Transcreve áudio usando o melhor backend disponível. Veja [STT](../media/stt.md).

## Text-to-Speech

```python
from omniachain import text_to_speech

result = await text_to_speech.execute(
    text="Olá mundo!",
    output_path="saida.mp3",
    voice="pt-BR-AntonioNeural",
    backend="edge",
)
```

Converte texto em áudio. Edge TTS é gratuito. Veja [TTS](../media/tts.md).

## Generate Image

```python
from omniachain import generate_image

result = await generate_image.execute(
    prompt="Um gato astronauta",
    output_path="gato.png",
    backend="openai",
)
```

Gera imagens com DALL-E, Nano Banana, Stability ou ComfyUI. Veja [Geração de Imagens](../media/image-gen.md).
