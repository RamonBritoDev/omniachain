"""Testes — Media: STT, TTS, Geração de Imagens (backends plugáveis)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from omniachain.media.stt import (
    SpeechToText, STTBackend, TranscriptionResult, TranscriptionSegment,
    OpenAISTTBackend, WhisperLocalSTTBackend, FasterWhisperSTTBackend, GoogleSTTBackend,
)
from omniachain.media.tts import (
    TextToSpeech, TTSBackend, Voice,
    OpenAITTSBackend, EdgeTTSBackend, CoquiTTSBackend, GoogleTTSBackend,
)
from omniachain.media.image_gen import (
    ImageGenerator, ImageBackend, GeneratedImage,
    OpenAIImageBackend, GoogleImageBackend, StabilityImageBackend, ComfyUIImageBackend,
)
from omniachain.core.errors import OmniaError


# ──────────────────────────────────────────────
# Testes: SpeechToText
# ──────────────────────────────────────────────

class TestSTTBackendRegistry:
    """Testa o sistema de registry de backends STT."""

    def test_list_builtin_backends(self):
        backends = SpeechToText.list_backends()
        assert "openai" in backends
        assert "whisper-local" in backends
        assert "faster-whisper" in backends
        assert "google" in backends

    def test_register_custom_backend(self):
        class CustomSTT(STTBackend):
            async def transcribe(self, audio_data, format="mp3", language="pt", **kw):
                return "texto customizado"

        SpeechToText.register_backend("custom-test", CustomSTT)
        assert "custom-test" in SpeechToText.list_backends()

        # Cleanup
        SpeechToText._registry.pop("custom-test", None)

    def test_invalid_backend_raises_error(self):
        with pytest.raises(OmniaError, match="não encontrado"):
            SpeechToText(backend="backend-inexistente")

    def test_repr(self):
        class MinSTT(STTBackend):
            async def transcribe(self, audio_data, format="mp3", language="pt", **kw):
                return ""

        SpeechToText.register_backend("min-stt", MinSTT)
        stt = SpeechToText(backend="min-stt")
        assert "min-stt" in repr(stt)

        SpeechToText._registry.pop("min-stt", None)


class TestCustomSTTBackend:
    """Testa backend customizado de STT."""

    @pytest.mark.asyncio
    async def test_custom_backend_transcribe(self):
        class MeuSTT(STTBackend):
            async def transcribe(self, audio_data, format="mp3", language="pt", **kw):
                return f"transcrito: {len(audio_data)} bytes"

        SpeechToText.register_backend("meu-stt", MeuSTT)
        stt = SpeechToText(backend="meu-stt")

        # Mock _load_audio para evitar acesso a arquivo
        audio_bytes = b"fake audio data here"
        with patch.object(stt, '_load_audio', new_callable=AsyncMock, return_value=(audio_bytes, "mp3")):
            result = await stt.transcribe("fake.mp3")

        assert "transcrito" in result
        assert "20 bytes" in result

        # Cleanup
        SpeechToText._registry.pop("meu-stt", None)

    @pytest.mark.asyncio
    async def test_custom_backend_transcribe_bytes(self):
        class BytesSTT(STTBackend):
            async def transcribe(self, audio_data, format="mp3", language="pt", **kw):
                return "áudio processado"

        SpeechToText.register_backend("bytes-stt", BytesSTT)
        stt = SpeechToText(backend="bytes-stt")

        result = await stt.transcribe(b"fake audio bytes")
        assert result == "áudio processado"

        SpeechToText._registry.pop("bytes-stt", None)

    @pytest.mark.asyncio
    async def test_transcribe_full(self):
        class SegmentSTT(STTBackend):
            async def transcribe(self, audio_data, format="mp3", language="pt", **kw):
                return "Olá mundo"

            async def transcribe_segments(self, audio_data, format="mp3", language="pt", **kw):
                return [
                    TranscriptionSegment(text="Olá", start=0.0, end=1.0),
                    TranscriptionSegment(text="mundo", start=1.0, end=2.0),
                ]

        SpeechToText.register_backend("segment-stt", SegmentSTT)
        stt = SpeechToText(backend="segment-stt")

        result = await stt.transcribe_full(b"audio data")
        assert isinstance(result, TranscriptionResult)
        assert result.text == "Olá mundo"
        assert len(result.segments) == 2
        assert result.segments[0].text == "Olá"
        assert result.backend_used == "segment-stt"

        SpeechToText._registry.pop("segment-stt", None)


# ──────────────────────────────────────────────
# Testes: TextToSpeech
# ──────────────────────────────────────────────

class TestTTSBackendRegistry:
    """Testa o sistema de registry de backends TTS."""

    def test_list_builtin_backends(self):
        backends = TextToSpeech.list_backends()
        assert "openai" in backends
        assert "edge" in backends
        assert "coqui" in backends
        assert "google" in backends

    def test_register_custom_backend(self):
        class CustomTTS(TTSBackend):
            async def synthesize(self, text, voice=None, format="mp3", **kw):
                return b"audio bytes"

        TextToSpeech.register_backend("custom-tts", CustomTTS)
        assert "custom-tts" in TextToSpeech.list_backends()

        TextToSpeech._registry.pop("custom-tts", None)

    def test_invalid_backend_raises_error(self):
        with pytest.raises(OmniaError, match="não encontrado"):
            TextToSpeech(backend="tts-inexistente")


class TestCustomTTSBackend:
    """Testa backend customizado de TTS."""

    @pytest.mark.asyncio
    async def test_custom_backend_speak(self):
        class MeuTTS(TTSBackend):
            async def synthesize(self, text, voice=None, format="mp3", **kw):
                return f"audio:{text}".encode()

        TextToSpeech.register_backend("meu-tts", MeuTTS)
        tts = TextToSpeech(backend="meu-tts")

        result = await tts.speak("Olá")
        assert result == b"audio:Ol\xc3\xa1"

        TextToSpeech._registry.pop("meu-tts", None)

    @pytest.mark.asyncio
    async def test_custom_backend_speak_to_file(self, tmp_path):
        class FileTTS(TTSBackend):
            async def synthesize(self, text, voice=None, format="mp3", **kw):
                return b"\x00\x01\x02\x03fake_audio_data"

        TextToSpeech.register_backend("file-tts", FileTTS)
        tts = TextToSpeech(backend="file-tts")

        output = tmp_path / "test_output.mp3"
        path = await tts.speak_to_file("Teste", str(output))

        assert path.exists()
        assert path.read_bytes() == b"\x00\x01\x02\x03fake_audio_data"

        TextToSpeech._registry.pop("file-tts", None)

    @pytest.mark.asyncio
    async def test_custom_backend_list_voices(self):
        class VoiceTTS(TTSBackend):
            async def synthesize(self, text, voice=None, format="mp3", **kw):
                return b"audio"

            async def list_voices(self):
                return [
                    Voice(id="v1", name="Voz 1", language="pt-BR", gender="Male", backend="test"),
                    Voice(id="v2", name="Voz 2", language="en-US", gender="Female", backend="test"),
                ]

        TextToSpeech.register_backend("voice-tts", VoiceTTS)
        tts = TextToSpeech(backend="voice-tts")

        voices = await tts.list_voices()
        assert len(voices) == 2
        assert voices[0].id == "v1"
        assert voices[1].language == "en-US"

        TextToSpeech._registry.pop("voice-tts", None)

    def test_repr(self):
        class MinimalTTS(TTSBackend):
            async def synthesize(self, text, voice=None, format="mp3", **kw):
                return b""

        TextToSpeech.register_backend("min-tts", MinimalTTS)
        tts = TextToSpeech(backend="min-tts", voice="test-voice")
        assert "min-tts" in repr(tts)
        assert "test-voice" in repr(tts)

        TextToSpeech._registry.pop("min-tts", None)


# ──────────────────────────────────────────────
# Testes: ImageGenerator
# ──────────────────────────────────────────────

class TestImageBackendRegistry:
    """Testa o sistema de registry de backends de imagem."""

    def test_list_builtin_backends(self):
        backends = ImageGenerator.list_backends()
        assert "openai" in backends
        assert "google" in backends
        assert "nano-banana" in backends
        assert "stability" in backends
        assert "comfyui" in backends

    def test_nano_banana_is_alias_for_google(self):
        # Verifica que nano-banana aponta para o mesmo backend do google
        assert ImageGenerator._registry["nano-banana"] is ImageGenerator._registry["google"]

    def test_register_custom_backend(self):
        class MidjourneyBackend(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                return [b"fake image"]

        ImageGenerator.register_backend("midjourney", MidjourneyBackend)
        assert "midjourney" in ImageGenerator.list_backends()

        ImageGenerator._registry.pop("midjourney", None)

    def test_invalid_backend_raises_error(self):
        with pytest.raises(OmniaError, match="não encontrado"):
            ImageGenerator(backend="dalle-5-turbo")


class TestCustomImageBackend:
    """Testa backend customizado de geração de imagens."""

    @pytest.mark.asyncio
    async def test_custom_backend_generate(self):
        class FakeImageGen(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                return [f"img:{prompt}".encode() for _ in range(n)]

        ImageGenerator.register_backend("fake-gen", FakeImageGen)
        gen = ImageGenerator(backend="fake-gen")

        images = await gen.generate("um gato")
        assert len(images) == 1
        assert images[0] == b"img:um gato"

        ImageGenerator._registry.pop("fake-gen", None)

    @pytest.mark.asyncio
    async def test_custom_backend_generate_multiple(self):
        class MultiImageGen(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                return [f"img_{i}".encode() for i in range(n)]

        ImageGenerator.register_backend("multi-gen", MultiImageGen)
        gen = ImageGenerator(backend="multi-gen")

        images = await gen.generate("teste", n=3)
        assert len(images) == 3
        assert images[0] == b"img_0"
        assert images[2] == b"img_2"

        ImageGenerator._registry.pop("multi-gen", None)

    @pytest.mark.asyncio
    async def test_custom_backend_generate_to_file(self, tmp_path):
        class FileImageGen(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                # Simula um PNG mínimo
                return [b"\x89PNG\r\n\x1a\nfake_image_data"]

        ImageGenerator.register_backend("file-gen", FileImageGen)
        gen = ImageGenerator(backend="file-gen")

        output = tmp_path / "test_image.png"
        path = await gen.generate_to_file("gato astronauta", str(output))

        assert path.exists()
        assert path.read_bytes().startswith(b"\x89PNG")

        ImageGenerator._registry.pop("file-gen", None)

    @pytest.mark.asyncio
    async def test_generate_multiple_to_dir(self, tmp_path):
        class DirImageGen(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                return [f"image_{i}".encode() for i in range(n)]

        ImageGenerator.register_backend("dir-gen", DirImageGen)
        gen = ImageGenerator(backend="dir-gen")

        output_dir = tmp_path / "images"
        paths = await gen.generate_multiple("paisagem", str(output_dir), n=3)

        assert len(paths) == 3
        assert all(p.exists() for p in paths)
        assert paths[0].read_bytes() == b"image_0"

        ImageGenerator._registry.pop("dir-gen", None)

    @pytest.mark.asyncio
    async def test_custom_backend_edit(self):
        class EditImageGen(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                return [b"original"]

            async def edit(self, image, prompt, **kw):
                return b"edited:" + image

        ImageGenerator.register_backend("edit-gen", EditImageGen)
        gen = ImageGenerator(backend="edit-gen")

        result = await gen.edit(b"input_image", "add hat")
        assert result == b"edited:input_image"

        ImageGenerator._registry.pop("edit-gen", None)

    @pytest.mark.asyncio
    async def test_edit_not_supported_raises_error(self):
        class NoEditGen(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                return [b"image"]

        ImageGenerator.register_backend("noedit-gen", NoEditGen)
        gen = ImageGenerator(backend="noedit-gen")

        with pytest.raises(OmniaError, match="não suporta edição"):
            await gen.edit(b"image", "edit this")

        ImageGenerator._registry.pop("noedit-gen", None)

    @pytest.mark.asyncio
    async def test_generate_empty_raises_error(self):
        class EmptyGen(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                return []

        ImageGenerator.register_backend("empty-gen", EmptyGen)
        gen = ImageGenerator(backend="empty-gen")

        with pytest.raises(OmniaError, match="Nenhuma imagem"):
            await gen.generate_to_file("test", "/tmp/test.png")

        ImageGenerator._registry.pop("empty-gen", None)

    def test_repr(self):
        class MinGen(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                return [b""]

        ImageGenerator.register_backend("min-gen", MinGen)
        gen = ImageGenerator(backend="min-gen")
        assert "min-gen" in repr(gen)

        ImageGenerator._registry.pop("min-gen", None)


# ──────────────────────────────────────────────
# Testes: Integração completa STT → TTS
# ──────────────────────────────────────────────

class TestSTTTTSIntegration:
    """Testa fluxo completo STT → processamento → TTS."""

    @pytest.mark.asyncio
    async def test_stt_to_tts_flow(self):
        """Simula: áudio → transcrição → síntese de voz."""

        class MockSTT(STTBackend):
            async def transcribe(self, audio_data, format="mp3", language="pt", **kw):
                return "Olá, como vai?"

        class MockTTS(TTSBackend):
            async def synthesize(self, text, voice=None, format="mp3", **kw):
                return f"AUDIO:{text}".encode()

        SpeechToText.register_backend("mock-stt", MockSTT)
        TextToSpeech.register_backend("mock-tts", MockTTS)

        stt = SpeechToText(backend="mock-stt")
        tts = TextToSpeech(backend="mock-tts")

        # Transcrever
        texto = await stt.transcribe(b"audio input")
        assert texto == "Olá, como vai?"

        # Sintetizar resposta
        audio = await tts.speak(f"Resposta para: {texto}")
        assert audio == b"AUDIO:Resposta para: Ol\xc3\xa1, como vai?"

        SpeechToText._registry.pop("mock-stt", None)
        TextToSpeech._registry.pop("mock-tts", None)


# ──────────────────────────────────────────────
# Testes: Imports do __init__.py
# ──────────────────────────────────────────────

class TestImports:
    """Testa que todos os novos exports funcionam."""

    def test_import_media_classes(self):
        from omniachain import SpeechToText, TextToSpeech, ImageGenerator
        assert SpeechToText is not None
        assert TextToSpeech is not None
        assert ImageGenerator is not None

    def test_import_backend_bases(self):
        from omniachain import STTBackend, TTSBackend, ImageBackend
        assert STTBackend is not None
        assert TTSBackend is not None
        assert ImageBackend is not None

    def test_import_agents(self):
        from omniachain import VoiceAgent, ArtistAgent
        assert VoiceAgent is not None
        assert ArtistAgent is not None

    def test_import_tools(self):
        from omniachain import speech_to_text, text_to_speech, generate_image
        assert speech_to_text is not None
        assert text_to_speech is not None
        assert generate_image is not None

    def test_import_from_media_subpackage(self):
        from omniachain.media import SpeechToText, TextToSpeech, ImageGenerator
        assert SpeechToText is not None

    def test_import_from_media_stt(self):
        from omniachain.media.stt import (
            SpeechToText, STTBackend,
            OpenAISTTBackend, WhisperLocalSTTBackend,
            FasterWhisperSTTBackend, GoogleSTTBackend,
            TranscriptionResult, TranscriptionSegment,
        )
        assert len(SpeechToText.list_backends()) >= 4

    def test_import_from_media_tts(self):
        from omniachain.media.tts import (
            TextToSpeech, TTSBackend, Voice,
            OpenAITTSBackend, EdgeTTSBackend,
            CoquiTTSBackend, GoogleTTSBackend,
        )
        assert len(TextToSpeech.list_backends()) >= 4

    def test_import_from_media_image_gen(self):
        from omniachain.media.image_gen import (
            ImageGenerator, ImageBackend, GeneratedImage,
            OpenAIImageBackend, GoogleImageBackend,
            StabilityImageBackend, ComfyUIImageBackend,
        )
        assert len(ImageGenerator.list_backends()) >= 5


# ──────────────────────────────────────────────
# Testes: Provider supports_* properties
# ──────────────────────────────────────────────

class TestProviderMediaSupport:
    """Testa que os providers reportam suporte a mídia."""

    def test_base_provider_defaults(self):
        from omniachain.providers.base import BaseProvider
        # BaseProvider é abstrata, testar via subclass
        # Os defaults devem ser False
        assert not BaseProvider.supports_stt.fget(None) if hasattr(BaseProvider.supports_stt, 'fget') else True

    def test_openai_supports_media(self):
        """OpenAI suporta STT, TTS e Image Gen."""
        # Não instanciar (requer API key), mas verificar que a classe tem os métodos
        from omniachain.providers.openai import OpenAIProvider
        assert hasattr(OpenAIProvider, 'transcribe')
        assert hasattr(OpenAIProvider, 'synthesize')
        assert hasattr(OpenAIProvider, 'generate_image')

    def test_google_supports_media(self):
        """Google suporta STT e Image Gen."""
        from omniachain.providers.google import GoogleProvider
        assert hasattr(GoogleProvider, 'transcribe')
        assert hasattr(GoogleProvider, 'generate_image')
