"""OmniaChain — Tool de Speech-to-Text para agentes."""

from omniachain.tools.base import tool


@tool(timeout=60.0, description="Transcreve um arquivo de áudio para texto usando STT.")
async def speech_to_text(file_path: str, language: str = "pt", backend: str = "auto") -> str:
    """Transcreve áudio para texto.

    Args:
        file_path: Caminho do arquivo de áudio (.mp3, .wav, .flac, etc.)
        language: Idioma do áudio (pt, en, es, etc.)
        backend: Backend de STT (auto, openai, whisper-local, faster-whisper, google)
    """
    from omniachain.media.stt import SpeechToText

    stt = SpeechToText(backend=backend, language=language)
    return await stt.transcribe(file_path)
