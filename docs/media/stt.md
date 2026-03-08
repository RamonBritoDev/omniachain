# Speech-to-Text (STT)

Transcrição de áudio com múltiplos backends — APIs e modelos locais.

## Backends

| Backend | Tipo | Requer | Velocidade |
|---------|------|--------|:----------:|
| `openai` | API | `OPENAI_API_KEY` | ⚡⚡⚡ |
| `whisper-local` | Local | `pip install openai-whisper` | ⚡⚡ |
| `faster-whisper` | Local | `pip install faster-whisper` | ⚡⚡⚡ |
| `google` | API | `pip install google-cloud-speech` | ⚡⚡⚡ |
| `auto` | — | Detecta automaticamente | — |

## Uso Básico

```python
from omniachain import SpeechToText

# Auto-detecta o melhor backend disponível
stt = SpeechToText()
texto = await stt.transcribe("audio.mp3")

# Backend específico
stt = SpeechToText(backend="openai", language="pt")
stt = SpeechToText(backend="whisper-local", model="large")
stt = SpeechToText(backend="faster-whisper", model="medium")
```

## Transcrição Completa

Retorna texto + segmentos com timestamps:

```python
result = await stt.transcribe_full("audio.mp3")

print(result.text)            # Texto completo
print(result.language)        # "pt"
print(result.backend_used)    # "faster-whisper"

for seg in result.segments:
    print(f"[{seg.start:.1f}s → {seg.end:.1f}s] {seg.text}")
```

## Aceita Múltiplos Inputs

```python
# Arquivo
texto = await stt.transcribe("audio.mp3")
texto = await stt.transcribe("podcast.wav")
texto = await stt.transcribe("musica.flac")

# Bytes
with open("audio.mp3", "rb") as f:
    texto = await stt.transcribe(f.read())

# Path
from pathlib import Path
texto = await stt.transcribe(Path("audio.mp3"))
```

## Backend Customizado

```python
from omniachain.media.stt import STTBackend, SpeechToText

class MinhaAPISTT(STTBackend):
    async def transcribe(self, audio_data, format="mp3", language="pt", **kw):
        # Chamar sua API aqui
        response = await minha_api.transcribe(audio_data)
        return response.text

SpeechToText.register_backend("minha-api", MinhaAPISTT)
stt = SpeechToText(backend="minha-api")
```

## Parâmetros

| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `backend` | `str` | `"auto"` | Backend a usar |
| `model` | `str` | `None` | Modelo (ex: `"large"` para Whisper) |
| `api_key` | `str` | `None` | API key (ou via env var) |
| `language` | `str` | `"pt"` | Idioma do áudio |

!!! note "Instalação"
    ```bash
    # Whisper local (offline)
    pip install openai-whisper

    # Faster-Whisper (~4x mais rápido)
    pip install faster-whisper
    ```
