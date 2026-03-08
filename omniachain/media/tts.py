"""
OmniaChain — Text-to-Speech com backends plugáveis.

Suporta APIs (OpenAI TTS, Google TTS) e gratuitos (Edge TTS, Coqui TTS).

Exemplo::

    from omniachain.media import TextToSpeech

    # Edge TTS — 100% gratuito, sem API key
    tts = TextToSpeech(backend="edge", voice="pt-BR-AntonioNeural")
    await tts.speak_to_file("Olá mundo!", "saida.mp3")

    # OpenAI TTS
    tts = TextToSpeech(backend="openai", voice="nova")
    audio_bytes = await tts.speak("Olá!")

    # Backend customizado
    TextToSpeech.register_backend("meu-tts", MeuTTSBackend)
"""

from __future__ import annotations

import abc
import os
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from omniachain.core.errors import OmniaError


class Voice(BaseModel):
    """Informações sobre uma voz disponível."""
    id: str
    name: str
    language: str = ""
    gender: str = ""
    backend: str = ""


class TTSResult(BaseModel):
    """Resultado de síntese de voz."""
    audio_data: bytes = b""
    format: str = "mp3"
    voice_used: str = ""
    backend_used: str = ""
    duration_estimate: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class TTSBackend(abc.ABC):
    """Classe base abstrata para backends de TTS.

    Para criar um backend customizado::

        class MeuTTS(TTSBackend):
            async def synthesize(self, text, voice=None, **kw):
                return b"audio bytes aqui"

        TextToSpeech.register_backend("meu-tts", MeuTTS)
    """

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs

    @abc.abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        format: str = "mp3",
        **kwargs: Any,
    ) -> bytes:
        """Converte texto em áudio.

        Args:
            text: Texto para sintetizar.
            voice: Identificador da voz.
            format: Formato de saída (mp3, wav, etc.).

        Returns:
            Bytes do áudio gerado.
        """
        ...

    async def list_voices(self) -> list[Voice]:
        """Lista vozes disponíveis."""
        return []


# ──────────────────────────────────────────────
# Backends built-in
# ──────────────────────────────────────────────

class OpenAITTSBackend(TTSBackend):
    """Backend TTS via OpenAI TTS API (tts-1, tts-1-hd)."""

    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    async def synthesize(
        self, text: str, voice: Optional[str] = None, format: str = "mp3", **kwargs: Any
    ) -> bytes:
        import openai

        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OmniaError(
                "OPENAI_API_KEY não configurada para TTS.",
                suggestion="Defina OPENAI_API_KEY ou passe api_key= no construtor.",
            )

        client = openai.AsyncOpenAI(api_key=api_key)
        model = self.config.get("model", "tts-1")
        voice = voice or self.config.get("voice", "nova")

        response = await client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format=format,
            **kwargs,
        )
        return response.content

    async def list_voices(self) -> list[Voice]:
        return [
            Voice(id=v, name=v.capitalize(), language="multi", backend="openai")
            for v in self.VOICES
        ]


class EdgeTTSBackend(TTSBackend):
    """Backend TTS via Microsoft Edge TTS — 100% GRATUITO, sem API key.

    Vozes de alta qualidade em pt-BR, en-US, es-ES e muitos outros idiomas.
    """

    DEFAULT_VOICES = {
        "pt-BR": "pt-BR-AntonioNeural",
        "pt": "pt-BR-AntonioNeural",
        "en": "en-US-GuyNeural",
        "en-US": "en-US-GuyNeural",
        "es": "es-ES-AlvaroNeural",
        "es-ES": "es-ES-AlvaroNeural",
    }

    async def synthesize(
        self, text: str, voice: Optional[str] = None, format: str = "mp3", **kwargs: Any
    ) -> bytes:
        try:
            import edge_tts
        except ImportError:
            raise OmniaError(
                "Edge TTS não instalado.",
                suggestion="Instale com: pip install edge-tts",
            )

        language = self.config.get("language", "pt-BR")
        voice = voice or self.config.get("voice") or self.DEFAULT_VOICES.get(
            language, "pt-BR-AntonioNeural"
        )

        communicate = edge_tts.Communicate(text, voice)
        audio_chunks: list[bytes] = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        return b"".join(audio_chunks)

    async def list_voices(self) -> list[Voice]:
        try:
            import edge_tts
        except ImportError:
            return []

        voices_list = await edge_tts.list_voices()
        return [
            Voice(
                id=v["ShortName"],
                name=v["FriendlyName"],
                language=v.get("Locale", ""),
                gender=v.get("Gender", ""),
                backend="edge",
            )
            for v in voices_list
        ]


class CoquiTTSBackend(TTSBackend):
    """Backend TTS via Coqui TTS — modelos locais (VITS, Tacotron2, etc.)."""

    async def synthesize(
        self, text: str, voice: Optional[str] = None, format: str = "wav", **kwargs: Any
    ) -> bytes:
        import asyncio

        try:
            from TTS.api import TTS as CoquiTTS
        except ImportError:
            raise OmniaError(
                "Coqui TTS não instalado.",
                suggestion="Instale com: pip install TTS",
            )

        model_name = self.config.get("model", "tts_models/pt/cv/vits")

        def _generate():
            import io
            import soundfile as sf
            import numpy as np

            tts = CoquiTTS(model_name=model_name)
            wav = tts.tts(text=text)
            buffer = io.BytesIO()
            sf.write(buffer, np.array(wav), samplerate=22050, format="WAV")
            return buffer.getvalue()

        return await asyncio.to_thread(_generate)


class GoogleTTSBackend(TTSBackend):
    """Backend TTS via Google Cloud Text-to-Speech."""

    async def synthesize(
        self, text: str, voice: Optional[str] = None, format: str = "mp3", **kwargs: Any
    ) -> bytes:
        import asyncio

        try:
            from google.cloud import texttospeech
        except ImportError:
            raise OmniaError(
                "Google Cloud TTS não instalado.",
                suggestion="Instale com: pip install google-cloud-texttospeech",
            )

        language = self.config.get("language", "pt-BR")

        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_params = texttospeech.VoiceSelectionParams(
            language_code=language,
            name=voice or self.config.get("voice"),
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
            if format == "mp3"
            else texttospeech.AudioEncoding.LINEAR16,
        )

        response = await asyncio.to_thread(
            client.synthesize_speech,
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        return response.audio_content


# ──────────────────────────────────────────────
# Classe principal
# ──────────────────────────────────────────────

class TextToSpeech:
    """Serviço de TTS com backends plugáveis.

    Exemplo::

        # Gratuito (Edge TTS)
        tts = TextToSpeech(backend="edge")
        await tts.speak_to_file("Olá mundo!", "saida.mp3")

        # OpenAI TTS
        tts = TextToSpeech(backend="openai", voice="nova")
        audio = await tts.speak("Olá!")

        # Registrar backend customizado
        TextToSpeech.register_backend("meu", MeuTTSBackend)
    """

    _registry: dict[str, type[TTSBackend]] = {
        "openai": OpenAITTSBackend,
        "edge": EdgeTTSBackend,
        "coqui": CoquiTTSBackend,
        "google": GoogleTTSBackend,
    }

    def __init__(
        self,
        backend: str = "auto",
        voice: Optional[str] = None,
        api_key: Optional[str] = None,
        language: str = "pt-BR",
        **kwargs: Any,
    ) -> None:
        self.backend_name = backend
        self.voice = voice
        self.language = language
        self._config = {"voice": voice, "api_key": api_key, "language": language, **kwargs}

        if backend == "auto":
            self._backend = self._auto_detect()
        else:
            if backend not in self._registry:
                raise OmniaError(
                    f"Backend TTS '{backend}' não encontrado.",
                    suggestion=f"Backends disponíveis: {', '.join(self._registry.keys())}. "
                    f"Ou registre um novo com TextToSpeech.register_backend()",
                )
            self._backend = self._registry[backend](**self._config)

    def _auto_detect(self) -> TTSBackend:
        """Detecta o melhor backend disponível."""
        # 1. Edge TTS (gratuito, sem API key)
        try:
            import edge_tts  # noqa: F401
            self.backend_name = "edge"
            return EdgeTTSBackend(**self._config)
        except ImportError:
            pass

        # 2. Coqui TTS (local)
        try:
            from TTS.api import TTS  # noqa: F401
            self.backend_name = "coqui"
            return CoquiTTSBackend(**self._config)
        except ImportError:
            pass

        # 3. OpenAI API
        if os.getenv("OPENAI_API_KEY") or self._config.get("api_key"):
            self.backend_name = "openai"
            return OpenAITTSBackend(**self._config)

        # 4. Google Cloud TTS
        try:
            from google.cloud import texttospeech  # noqa: F401
            self.backend_name = "google"
            return GoogleTTSBackend(**self._config)
        except ImportError:
            pass

        raise OmniaError(
            "Nenhum backend de TTS disponível.",
            suggestion="Instale um backend: pip install edge-tts (gratuito), "
            "pip install TTS, ou defina OPENAI_API_KEY.",
        )

    @classmethod
    def register_backend(cls, name: str, backend_class: type[TTSBackend]) -> None:
        """Registra um backend customizado de TTS."""
        cls._registry[name] = backend_class

    @classmethod
    def list_backends(cls) -> list[str]:
        """Lista todos os backends registrados."""
        return list(cls._registry.keys())

    async def speak(self, text: str, **kwargs: Any) -> bytes:
        """Converte texto em áudio (retorna bytes).

        Args:
            text: Texto para sintetizar.
            **kwargs: Argumentos extras para o backend.

        Returns:
            Bytes do áudio gerado.
        """
        return await self._backend.synthesize(text, voice=self.voice, **kwargs)

    async def speak_to_file(
        self, text: str, output_path: Union[str, Path], **kwargs: Any
    ) -> Path:
        """Converte texto e salva direto em arquivo.

        Args:
            text: Texto para sintetizar.
            output_path: Caminho do arquivo de saída.

        Returns:
            Path do arquivo criado.
        """
        import aiofiles

        audio_data = await self.speak(text, **kwargs)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, "wb") as f:
            await f.write(audio_data)

        return path

    async def list_voices(self) -> list[Voice]:
        """Lista vozes disponíveis no backend atual."""
        return await self._backend.list_voices()

    def __repr__(self) -> str:
        return f"TextToSpeech(backend={self.backend_name!r}, voice={self.voice!r})"
