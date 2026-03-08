"""OmniaChain — Loader de áudio (.mp3, .wav) com transcrição."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import MessageContent
from omniachain.loaders.base import BaseLoader


class AudioLoader(BaseLoader):
    """Carrega arquivos de áudio e opcionalmente transcreve via Whisper.

    Exemplo::

        loader = AudioLoader(transcribe=True)
        content = await loader.load("audio.mp3")
        print(content.data)  # Texto transcrito
    """

    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac"}

    def __init__(self, transcribe: bool = True) -> None:
        self.transcribe = transcribe

    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Carrega áudio e retorna MessageContent (texto transcrito ou dados raw)."""
        try:
            if isinstance(source, bytes):
                audio_data = source
                metadata: dict = {"format": "unknown"}
            else:
                path = Path(str(source))
                audio_data = await self._read_file(path)
                metadata = self._get_metadata(path)
                metadata["format"] = path.suffix.lower().lstrip(".")

            metadata["size_bytes"] = len(audio_data)

            if self.transcribe:
                transcription = await self._transcribe(audio_data, metadata.get("format", "mp3"))
                metadata["transcribed"] = True
                content = MessageContent.text(transcription)
                content.metadata.update(metadata)
                return content
            else:
                import base64
                b64 = base64.b64encode(audio_data).decode("ascii")
                mime = f"audio/{metadata.get('format', 'mp3')}"
                return MessageContent.audio(b64, mime_type=mime, **metadata)

        except LoaderError:
            raise
        except Exception as e:
            raise LoaderError(
                f"Erro ao carregar áudio: {e}",
                loader="AudioLoader",
                source=str(source),
                original_error=e,
            )

    async def _transcribe(self, audio_data: bytes, format: str = "mp3") -> str:
        """Transcreve áudio usando OpenAI Whisper API ou local."""
        import asyncio

        # Tenta Whisper local primeiro
        try:
            import whisper
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            try:
                model = whisper.load_model("base")
                result = await asyncio.to_thread(model.transcribe, temp_path)
                return result.get("text", "")
            finally:
                os.unlink(temp_path)

        except ImportError:
            pass

        # Fallback: OpenAI Whisper API
        try:
            import openai
            import os
            import tempfile
            import io

            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{format}"

            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
            return transcript.text

        except Exception as e:
            raise LoaderError(
                "Não foi possível transcrever o áudio.",
                loader="AudioLoader",
                source="bytes",
                suggestion="Instale whisper (pip install openai-whisper) ou configure OPENAI_API_KEY.",
                original_error=e,
            )
