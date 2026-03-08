"""OmniaChain — Tool de Text-to-Speech para agentes."""

from omniachain.tools.base import tool


@tool(timeout=60.0, description="Converte texto em áudio e salva em arquivo.")
async def text_to_speech(
    text: str,
    output_path: str = "output.mp3",
    voice: str = "pt-BR-AntonioNeural",
    backend: str = "auto",
) -> str:
    """Converte texto em áudio.

    Args:
        text: Texto para converter em fala.
        output_path: Caminho do arquivo de saída (.mp3)
        voice: Voz a utilizar.
        backend: Backend de TTS (auto, openai, edge, coqui, google)
    """
    from omniachain.media.tts import TextToSpeech

    tts = TextToSpeech(backend=backend, voice=voice)
    path = await tts.speak_to_file(text, output_path)
    return f"Áudio salvo em: {path}"
