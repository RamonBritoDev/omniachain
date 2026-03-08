"""
OmniaChain — Speech-to-Text com backends plugáveis.

Suporta APIs (OpenAI Whisper, Google Speech) e modelos locais (Whisper, Faster-Whisper).

Exemplo::

    from omniachain.media import SpeechToText

    # Auto-detecta melhor backend disponível
    stt = SpeechToText()
    texto = await stt.transcribe("audio.mp3")

    # Backend específico
    stt = SpeechToText(backend="openai")
    stt = SpeechToText(backend="whisper-local", model="large")

    # Backend customizado
    class MeuSTT(STTBackend):
        async def transcribe(self, audio_data, format, language):
            return "texto transcrito"

    SpeechToText.register_backend("meu-stt", MeuSTT)
    stt = SpeechToText(backend="meu-stt")
"""

from __future__ import annotations

import abc
import io
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from omniachain.core.errors import OmniaError


class TranscriptionSegment(BaseModel):
    """Segmento de transcrição com timestamps."""
    text: str
    start: float = 0.0
    end: float = 0.0
    confidence: float = 0.0


class TranscriptionResult(BaseModel):
    """Resultado completo de uma transcrição."""
    text: str
    language: str = ""
    duration: float = 0.0
    segments: list[TranscriptionSegment] = Field(default_factory=list)
    backend_used: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class STTBackend(abc.ABC):
    """Classe base abstrata para backends de STT.

    Para criar um backend customizado, herde desta classe e implemente `transcribe`.

    Exemplo::

        class MeuBackend(STTBackend):
            async def transcribe(self, audio_data, format="mp3", language="pt"):
                # sua lógica aqui
                return "texto transcrito"
    """

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs

    @abc.abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        format: str = "mp3",
        language: str = "pt",
        **kwargs: Any,
    ) -> str:
        """Transcreve áudio para texto.

        Args:
            audio_data: Bytes do arquivo de áudio.
            format: Formato do áudio (mp3, wav, flac, etc.).
            language: Código do idioma (pt, en, es, etc.).

        Returns:
            Texto transcrito.
        """
        ...

    async def transcribe_segments(
        self,
        audio_data: bytes,
        format: str = "mp3",
        language: str = "pt",
        **kwargs: Any,
    ) -> list[TranscriptionSegment]:
        """Transcreve com timestamps por segmento (quando suportado)."""
        text = await self.transcribe(audio_data, format, language, **kwargs)
        return [TranscriptionSegment(text=text)]


# ──────────────────────────────────────────────
# Backends built-in
# ──────────────────────────────────────────────

class OpenAISTTBackend(STTBackend):
    """Backend STT via OpenAI Whisper API."""

    async def transcribe(
        self, audio_data: bytes, format: str = "mp3", language: str = "pt", **kwargs: Any
    ) -> str:
        import openai

        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OmniaError(
                "OPENAI_API_KEY não configurada para STT.",
                suggestion="Defina OPENAI_API_KEY ou passe api_key= no construtor.",
            )

        client = openai.AsyncOpenAI(api_key=api_key)
        audio_file = io.BytesIO(audio_data)
        audio_file.name = f"audio.{format}"

        transcript = await client.audio.transcriptions.create(
            model=self.config.get("model", "whisper-1"),
            file=audio_file,
            language=language,
            **kwargs,
        )
        return transcript.text


class WhisperLocalSTTBackend(STTBackend):
    """Backend STT via Whisper rodando 100% local."""

    async def transcribe(
        self, audio_data: bytes, format: str = "mp3", language: str = "pt", **kwargs: Any
    ) -> str:
        import asyncio

        try:
            import whisper
        except ImportError:
            raise OmniaError(
                "Whisper local não instalado.",
                suggestion="Instale com: pip install openai-whisper",
            )

        model_name = self.config.get("model", "base")

        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            model = whisper.load_model(model_name)
            result = await asyncio.to_thread(
                model.transcribe, temp_path, language=language
            )
            return result.get("text", "")
        finally:
            os.unlink(temp_path)

    async def transcribe_segments(
        self, audio_data: bytes, format: str = "mp3", language: str = "pt", **kwargs: Any
    ) -> list[TranscriptionSegment]:
        import asyncio

        try:
            import whisper
        except ImportError:
            raise OmniaError(
                "Whisper local não instalado.",
                suggestion="Instale com: pip install openai-whisper",
            )

        model_name = self.config.get("model", "base")

        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            model = whisper.load_model(model_name)
            result = await asyncio.to_thread(
                model.transcribe, temp_path, language=language
            )
            segments = []
            for seg in result.get("segments", []):
                segments.append(TranscriptionSegment(
                    text=seg.get("text", ""),
                    start=seg.get("start", 0.0),
                    end=seg.get("end", 0.0),
                    confidence=seg.get("avg_logprob", 0.0),
                ))
            return segments
        finally:
            os.unlink(temp_path)


class FasterWhisperSTTBackend(STTBackend):
    """Backend STT via Faster-Whisper (CTranslate2, ~4x mais rápido)."""

    async def transcribe(
        self, audio_data: bytes, format: str = "mp3", language: str = "pt", **kwargs: Any
    ) -> str:
        import asyncio

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise OmniaError(
                "Faster-Whisper não instalado.",
                suggestion="Instale com: pip install faster-whisper",
            )

        model_name = self.config.get("model", "base")

        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            model = WhisperModel(model_name, compute_type="int8")
            segments_gen, info = await asyncio.to_thread(
                model.transcribe, temp_path, language=language
            )
            segments = list(segments_gen)
            return " ".join(seg.text.strip() for seg in segments)
        finally:
            os.unlink(temp_path)


class GoogleSTTBackend(STTBackend):
    """Backend STT via Google Cloud Speech-to-Text."""

    async def transcribe(
        self, audio_data: bytes, format: str = "mp3", language: str = "pt", **kwargs: Any
    ) -> str:
        import asyncio

        try:
            from google.cloud import speech
        except ImportError:
            raise OmniaError(
                "Google Cloud Speech não instalado.",
                suggestion="Instale com: pip install google-cloud-speech",
            )

        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_data)

        encoding_map = {
            "mp3": speech.RecognitionConfig.AudioEncoding.MP3,
            "wav": speech.RecognitionConfig.AudioEncoding.LINEAR16,
            "flac": speech.RecognitionConfig.AudioEncoding.FLAC,
            "ogg": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        }

        config = speech.RecognitionConfig(
            encoding=encoding_map.get(format, speech.RecognitionConfig.AudioEncoding.MP3),
            language_code=language if "-" in language else f"{language}-BR",
            enable_automatic_punctuation=True,
        )

        response = await asyncio.to_thread(client.recognize, config=config, audio=audio)
        texts = [r.alternatives[0].transcript for r in response.results if r.alternatives]
        return " ".join(texts)


# ──────────────────────────────────────────────
# Classe principal
# ──────────────────────────────────────────────

class SpeechToText:
    """Serviço de STT com backends plugáveis.

    Exemplo::

        stt = SpeechToText(backend="openai")
        texto = await stt.transcribe("audio.mp3")

        stt = SpeechToText(backend="whisper-local", model="large")
        texto = await stt.transcribe(audio_bytes)

        # Registrar backend customizado
        SpeechToText.register_backend("meu-stt", MeuSTTBackend)
    """

    _registry: dict[str, type[STTBackend]] = {
        "openai": OpenAISTTBackend,
        "whisper-local": WhisperLocalSTTBackend,
        "faster-whisper": FasterWhisperSTTBackend,
        "google": GoogleSTTBackend,
    }

    def __init__(
        self,
        backend: str = "auto",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        language: str = "pt",
        **kwargs: Any,
    ) -> None:
        self.backend_name = backend
        self.language = language
        self._config = {"model": model, "api_key": api_key, **kwargs}

        if backend == "auto":
            self._backend = self._auto_detect()
        else:
            if backend not in self._registry:
                raise OmniaError(
                    f"Backend STT '{backend}' não encontrado.",
                    suggestion=f"Backends disponíveis: {', '.join(self._registry.keys())}. "
                    f"Ou registre um novo com SpeechToText.register_backend()",
                )
            self._backend = self._registry[backend](**self._config)

    def _auto_detect(self) -> STTBackend:
        """Detecta o melhor backend disponível."""
        # 1. Faster-Whisper (mais rápido local)
        try:
            from faster_whisper import WhisperModel  # noqa: F401
            self.backend_name = "faster-whisper"
            return FasterWhisperSTTBackend(**self._config)
        except ImportError:
            pass

        # 2. Whisper local
        try:
            import whisper  # noqa: F401
            self.backend_name = "whisper-local"
            return WhisperLocalSTTBackend(**self._config)
        except ImportError:
            pass

        # 3. OpenAI API
        if os.getenv("OPENAI_API_KEY") or self._config.get("api_key"):
            self.backend_name = "openai"
            return OpenAISTTBackend(**self._config)

        # 4. Google
        try:
            from google.cloud import speech  # noqa: F401
            self.backend_name = "google"
            return GoogleSTTBackend(**self._config)
        except ImportError:
            pass

        raise OmniaError(
            "Nenhum backend de STT disponível.",
            suggestion="Instale um backend: pip install openai-whisper, "
            "pip install faster-whisper, ou defina OPENAI_API_KEY.",
        )

    @classmethod
    def register_backend(cls, name: str, backend_class: type[STTBackend]) -> None:
        """Registra um backend customizado de STT.

        Exemplo::

            class MeuSTT(STTBackend):
                async def transcribe(self, audio_data, format, language, **kw):
                    return "transcricao"

            SpeechToText.register_backend("meu-stt", MeuSTT)
        """
        cls._registry[name] = backend_class

    @classmethod
    def list_backends(cls) -> list[str]:
        """Lista todos os backends registrados."""
        return list(cls._registry.keys())

    async def transcribe(self, source: Union[str, Path, bytes], **kwargs: Any) -> str:
        """Transcreve áudio para texto.

        Args:
            source: Caminho do arquivo, bytes, ou Path.
            **kwargs: Argumentos extras para o backend.

        Returns:
            Texto transcrito.
        """
        audio_data, fmt = await self._load_audio(source)
        return await self._backend.transcribe(
            audio_data, format=fmt, language=self.language, **kwargs
        )

    async def transcribe_full(
        self, source: Union[str, Path, bytes], **kwargs: Any
    ) -> TranscriptionResult:
        """Transcreve com resultado completo (texto + segmentos + metadados)."""
        audio_data, fmt = await self._load_audio(source)
        text = await self._backend.transcribe(
            audio_data, format=fmt, language=self.language, **kwargs
        )
        segments = await self._backend.transcribe_segments(
            audio_data, format=fmt, language=self.language, **kwargs
        )
        return TranscriptionResult(
            text=text,
            language=self.language,
            segments=segments,
            backend_used=self.backend_name,
        )

    async def _load_audio(self, source: Union[str, Path, bytes]) -> tuple[bytes, str]:
        """Carrega áudio de arquivo ou bytes."""
        if isinstance(source, bytes):
            return source, "mp3"

        import aiofiles

        path = Path(str(source))
        if not path.exists():
            raise OmniaError(
                f"Arquivo de áudio não encontrado: {path}",
                suggestion="Verifique se o caminho está correto.",
            )

        async with aiofiles.open(path, "rb") as f:
            data = await f.read()

        fmt = path.suffix.lower().lstrip(".")
        return data, fmt

    def __repr__(self) -> str:
        return f"SpeechToText(backend={self.backend_name!r})"
