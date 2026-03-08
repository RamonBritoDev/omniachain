# Text-to-Speech (TTS)

Síntese de voz com múltiplos backends — incluindo opções 100% gratuitas.

## Backends

| Backend | Tipo | Requer | Custo | Qualidade |
|---------|------|--------|:-----:|:---------:|
| `edge` ⭐ | Grátis | `pip install edge-tts` | **Grátis** | ⭐⭐⭐⭐ |
| `openai` | API | `OPENAI_API_KEY` | $0.015/1K chars | ⭐⭐⭐⭐⭐ |
| `coqui` | Local | `pip install TTS` | **Grátis** | ⭐⭐⭐ |
| `google` | API | `pip install google-cloud-texttospeech` | $4/1M chars | ⭐⭐⭐⭐ |
| `auto` | — | Detecta automaticamente | — | — |

!!! tip "Recomendação"
    **Edge TTS** é a melhor opção para começar — qualidade excelente, grátis, sem API key, vozes em pt-BR.

## Uso Básico

```python
from omniachain import TextToSpeech

# Edge TTS (grátis)
tts = TextToSpeech(backend="edge", voice="pt-BR-AntonioNeural")
await tts.speak_to_file("Olá, como vai?", "saida.mp3")

# OpenAI TTS
tts = TextToSpeech(backend="openai", voice="nova")
audio_bytes = await tts.speak("Olá mundo!")

# Auto-detecta (Edge TTS por padrão)
tts = TextToSpeech()
await tts.speak_to_file("Teste", "teste.mp3")
```

## Vozes Disponíveis

### Edge TTS (pt-BR)

| Voz | Gender | ID |
|-----|--------|-----|
| Antônio | Masculino | `pt-BR-AntonioNeural` |
| Francisca | Feminino | `pt-BR-FranciscaNeural` |

### OpenAI

| Voz | Estilo |
|-----|--------|
| `alloy` | Neutro |
| `echo` | Masculino |
| `fable` | Britânico |
| `onyx` | Grave |
| `nova` | Feminino |
| `shimmer` | Suave |

### Listar Vozes Programaticamente

```python
tts = TextToSpeech(backend="edge")
voices = await tts.list_voices()

# Filtrar vozes pt-BR
for v in voices:
    if "pt-BR" in v.language:
        print(f"{v.name} ({v.id}) — {v.gender}")
```

## Salvar em Arquivo

```python
tts = TextToSpeech(backend="edge")

# Salva MP3
path = await tts.speak_to_file("Texto aqui", "audio.mp3")
print(f"Salvo em: {path}")

# Cria diretórios automaticamente
await tts.speak_to_file("Teste", "audios/output/teste.mp3")
```

## Obter Bytes

```python
tts = TextToSpeech(backend="openai", voice="nova")

# Retorna bytes do áudio
audio = await tts.speak("Olá mundo!")

# Usar com outro serviço
import base64
b64 = base64.b64encode(audio).decode()
```

## Backend Customizado

```python
from omniachain.media.tts import TTSBackend, TextToSpeech, Voice

class ElevenLabsTTS(TTSBackend):
    async def synthesize(self, text, voice=None, format="mp3", **kw):
        response = await eleven_labs_api.generate(text=text, voice_id=voice)
        return response.audio

    async def list_voices(self):
        voices = await eleven_labs_api.list_voices()
        return [Voice(id=v.id, name=v.name, backend="elevenlabs") for v in voices]

TextToSpeech.register_backend("elevenlabs", ElevenLabsTTS)
tts = TextToSpeech(backend="elevenlabs", voice="Rachel")
```

## Parâmetros

| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `backend` | `str` | `"auto"` | Backend a usar |
| `voice` | `str` | `None` | Voz específica |
| `api_key` | `str` | `None` | API key (ou via env var) |
| `language` | `str` | `"pt-BR"` | Idioma |

!!! note "Instalação"
    ```bash
    # Edge TTS (recomendado, grátis)
    pip install edge-tts

    # Coqui TTS (local, offline)
    pip install TTS
    ```
