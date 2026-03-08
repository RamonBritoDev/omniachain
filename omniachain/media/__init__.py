"""
OmniaChain — Módulo de mídia: STT, TTS e geração de imagens.

Backends plugáveis para qualquer API ou modelo local.

Exemplo::

    from omniachain.media import SpeechToText, TextToSpeech, ImageGenerator

    stt = SpeechToText(backend="whisper-local")
    tts = TextToSpeech(backend="edge")
    gen = ImageGenerator(backend="openai")
"""

from omniachain.media.stt import SpeechToText, STTBackend
from omniachain.media.tts import TextToSpeech, TTSBackend
from omniachain.media.image_gen import ImageGenerator, ImageBackend

__all__ = [
    "SpeechToText", "STTBackend",
    "TextToSpeech", "TTSBackend",
    "ImageGenerator", "ImageBackend",
]
