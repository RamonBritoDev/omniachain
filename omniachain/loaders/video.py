"""
OmniaChain — VideoLoader avançado: frames-chave + transcrição de áudio + metadados.

Extrai:
1. Frames-chave do vídeo em base64 (para modelos de visão)
2. Áudio do vídeo → transcrição via Whisper
3. Metadados completos (duração, resolução, título)

Requer ffmpeg instalado no sistema para extração de frames e áudio.

Exemplo::

    loader = VideoLoader(num_frames=6, transcribe_audio=True)
    contents = await loader.load("video.mp4")
    # Retorna lista: [texto_resumo, frame1, frame2, ..., transcrição]

    # YouTube também funciona:
    contents = await loader.load("https://youtube.com/watch?v=abc123")
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import ContentType, MessageContent
from omniachain.loaders.base import BaseLoader

YOUTUBE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


class VideoLoader(BaseLoader):
    """Loader avançado de vídeo com extração de frames e áudio.

    Processa vídeos em 3 camadas:
    - **Frames-chave**: Extrai N frames distribuídos ao longo do vídeo → base64
    - **Áudio**: Extrai trilha sonora → transcrição via Whisper
    - **Metadados**: Duração, resolução, codec, etc.

    Exemplo::

        loader = VideoLoader(num_frames=6, transcribe_audio=True)
        contents = await loader.load("apresentacao.mp4")

        # Para YouTube:
        contents = await loader.load("https://youtube.com/watch?v=abc")
    """

    SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv", ".wmv"}

    def __init__(
        self,
        num_frames: int = 4,
        transcribe_audio: bool = True,
        max_audio_duration: int = 600,  # 10 min máximo para transcrição
    ) -> None:
        self.num_frames = num_frames
        self.transcribe_audio = transcribe_audio
        self.max_audio_duration = max_audio_duration

    @classmethod
    def is_youtube_url(cls, source: str) -> bool:
        """Verifica se a source é uma URL do YouTube."""
        return bool(YOUTUBE_REGEX.search(str(source)))

    async def load(self, source: Union[str, Path, bytes]) -> list[MessageContent]:
        """Carrega vídeo e retorna lista de conteúdos multi-modais.

        Returns:
            Lista contendo:
            - [0] Resumo/metadados (texto)
            - [1..N] Frames-chave (imagens base64)
            - [N+1] Transcrição do áudio (texto, se habilitado)
        """
        try:
            source_str = str(source)

            if isinstance(source, str) and self.is_youtube_url(source_str):
                return await self._load_youtube(source_str)
            else:
                return await self._load_local(source)

        except LoaderError:
            raise
        except Exception as e:
            raise LoaderError(
                f"Erro ao carregar vídeo: {e}",
                loader="VideoLoader",
                source=str(source),
                original_error=e,
            )

    # ─── YOUTUBE ──────────────────────────────────────────────────────────

    async def _load_youtube(self, url: str) -> list[MessageContent]:
        """Baixa vídeo do YouTube, extrai frames + áudio."""
        try:
            import yt_dlp
        except ImportError:
            raise LoaderError(
                "Pacote 'yt-dlp' não instalado.",
                loader="VideoLoader",
                source=url,
                suggestion="Instale com: pip install yt-dlp",
            )

        temp_dir = tempfile.mkdtemp(prefix="omniachain_yt_")

        try:
            # Baixar vídeo
            ydl_opts = {
                "format": "worst[ext=mp4]/worst",
                "outtmpl": os.path.join(temp_dir, "video.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
            }

            def _download() -> dict:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True) or {}

            info = await asyncio.to_thread(_download)

            video_path = os.path.join(temp_dir, "video.mp4")
            if not os.path.exists(video_path):
                # Tentar encontrar qualquer vídeo baixado
                for f in os.listdir(temp_dir):
                    if f.startswith("video."):
                        video_path = os.path.join(temp_dir, f)
                        break

            metadata = {
                "source": "youtube",
                "url": url,
                "title": info.get("title", ""),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", ""),
                "view_count": info.get("view_count", 0),
                "description": (info.get("description", "") or "")[:500],
            }

            # Extrair frames + áudio do vídeo baixado
            contents = await self._process_video_file(video_path, temp_dir, metadata)
            return contents

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ─── LOCAL ────────────────────────────────────────────────────────────

    async def _load_local(self, source: Union[str, Path, bytes]) -> list[MessageContent]:
        """Carrega vídeo local, extrai frames + áudio."""
        temp_dir = tempfile.mkdtemp(prefix="omniachain_vid_")

        try:
            if isinstance(source, bytes):
                # Salvar bytes em temp file
                video_path = os.path.join(temp_dir, "input_video.mp4")
                with open(video_path, "wb") as f:
                    f.write(source)
                metadata: dict[str, Any] = {"format": "mp4", "size_bytes": len(source)}
            else:
                path = Path(str(source))
                if not path.exists():
                    raise LoaderError(
                        f"Vídeo não encontrado: {source}",
                        loader="VideoLoader",
                        source=str(source),
                    )
                video_path = str(path)
                metadata = self._get_metadata(path)

            contents = await self._process_video_file(video_path, temp_dir, metadata)
            return contents

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ─── PROCESSAMENTO PRINCIPAL ──────────────────────────────────────────

    async def _process_video_file(
        self,
        video_path: str,
        temp_dir: str,
        metadata: dict[str, Any],
    ) -> list[MessageContent]:
        """Processa um arquivo de vídeo: extrai frames + áudio + metadados.

        Retorna lista de MessageContent com tudo combinado.
        """
        contents: list[MessageContent] = []

        # 1. Obter duração e info do vídeo via ffprobe
        probe_info = await self._get_video_info(video_path)
        metadata.update(probe_info)

        # 2. Resumo textual do vídeo
        summary = self._build_summary(video_path, metadata)
        contents.append(MessageContent(
            type=ContentType.TEXT,
            data=summary,
            metadata={"role": "video_summary", **metadata},
        ))

        # 3. Extrair frames-chave como imagens base64
        if self.num_frames > 0:
            frames = await self._extract_frames(video_path, temp_dir, metadata)
            contents.extend(frames)

        # 4. Extrair e transcrever áudio
        if self.transcribe_audio:
            transcription = await self._extract_and_transcribe_audio(video_path, temp_dir)
            if transcription:
                contents.append(MessageContent(
                    type=ContentType.TEXT,
                    data=f"[Transcrição do áudio do vídeo]\n{transcription}",
                    metadata={"role": "audio_transcription"},
                ))

        return contents

    # ─── FRAMES ───────────────────────────────────────────────────────────

    async def _extract_frames(
        self,
        video_path: str,
        temp_dir: str,
        metadata: dict[str, Any],
    ) -> list[MessageContent]:
        """Extrai N frames distribuídos ao longo do vídeo."""
        if not await self._check_ffmpeg():
            return [MessageContent(
                type=ContentType.TEXT,
                data="[ffmpeg não disponível — frames não extraídos]",
                metadata={"role": "frame_error"},
            )]

        duration = metadata.get("duration", 0)
        if not duration:
            duration = 60  # Fallback

        # Calcular timestamps para frames distribuídos uniformemente
        interval = max(duration / (self.num_frames + 1), 1)
        timestamps = [interval * (i + 1) for i in range(self.num_frames)]

        frames: list[MessageContent] = []

        for i, ts in enumerate(timestamps):
            frame_path = os.path.join(temp_dir, f"frame_{i:03d}.jpg")

            try:
                # ffmpeg extrai frame no timestamp
                process = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-ss", str(ts), "-i", video_path,
                    "-vframes", "1", "-q:v", "2",
                    "-y", frame_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(process.wait(), timeout=15)

                if os.path.exists(frame_path) and os.path.getsize(frame_path) > 0:
                    with open(frame_path, "rb") as f:
                        frame_data = base64.b64encode(f.read()).decode()

                    frames.append(MessageContent(
                        type=ContentType.IMAGE,
                        data=frame_data,
                        mime_type="image/jpeg",
                        metadata={
                            "role": "video_frame",
                            "frame_index": i,
                            "timestamp_seconds": round(ts, 1),
                            "description": f"Frame {i+1}/{self.num_frames} em {ts:.1f}s",
                        },
                    ))

            except (asyncio.TimeoutError, Exception):
                continue

        return frames

    # ─── ÁUDIO ────────────────────────────────────────────────────────────

    async def _extract_and_transcribe_audio(
        self,
        video_path: str,
        temp_dir: str,
    ) -> str:
        """Extrai áudio do vídeo e transcreve com Whisper."""
        if not await self._check_ffmpeg():
            return ""

        audio_path = os.path.join(temp_dir, "audio.wav")

        try:
            # 1. Extrair áudio com ffmpeg
            process = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", video_path,
                "-vn",                    # Sem vídeo
                "-acodec", "pcm_s16le",   # WAV PCM
                "-ar", "16000",           # 16kHz (Whisper)
                "-ac", "1",               # Mono
                "-t", str(self.max_audio_duration),  # Limitar duração
                "-y", audio_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(process.wait(), timeout=60)

            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
                return ""

            # 2. Transcrever com Whisper
            transcription = await self._transcribe_with_whisper(audio_path)
            if transcription:
                return transcription

            # 3. Fallback: transcrever com OpenAI API
            transcription = await self._transcribe_with_openai(audio_path)
            if transcription:
                return transcription

            return "[Áudio extraído mas transcrição não disponível — instale whisper ou configure OPENAI_API_KEY]"

        except (asyncio.TimeoutError, Exception) as e:
            return f"[Erro ao extrair áudio: {e}]"

    async def _transcribe_with_whisper(self, audio_path: str) -> str:
        """Transcreve com Whisper local (se instalado)."""
        try:
            import whisper

            model = await asyncio.to_thread(whisper.load_model, "base")
            result = await asyncio.to_thread(model.transcribe, audio_path)
            return result.get("text", "")

        except ImportError:
            return ""
        except Exception:
            return ""

    async def _transcribe_with_openai(self, audio_path: str) -> str:
        """Transcreve com OpenAI Whisper API (se disponível)."""
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return ""

            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_path, "rb") as f:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": ("audio.wav", f, "audio/wav")},
                        data={"model": "whisper-1"},
                    )
                    response.raise_for_status()
                    return response.json().get("text", "")

        except Exception:
            return ""

    # ─── UTILS ────────────────────────────────────────────────────────────

    async def _check_ffmpeg(self) -> bool:
        """Verifica se ffmpeg está disponível no sistema."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg", "-version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(process.wait(), timeout=5)
            return process.returncode == 0
        except Exception:
            return False

    async def _get_video_info(self, video_path: str) -> dict[str, Any]:
        """Obtém info do vídeo via ffprobe."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                video_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)

            import json
            data = json.loads(stdout.decode())

            fmt = data.get("format", {})
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                {},
            )
            audio_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
                {},
            )

            return {
                "duration": float(fmt.get("duration", 0)),
                "size_bytes": int(fmt.get("size", 0)),
                "bitrate": int(fmt.get("bit_rate", 0)),
                "format_name": fmt.get("format_name", ""),
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream.get("r_frame_rate") else 0,
                "video_codec": video_stream.get("codec_name", ""),
                "audio_codec": audio_stream.get("codec_name", ""),
                "audio_sample_rate": int(audio_stream.get("sample_rate", 0)),
                "has_audio": bool(audio_stream),
            }

        except Exception:
            return {"duration": 0}

    def _build_summary(self, video_path: str, metadata: dict[str, Any]) -> str:
        """Constrói resumo textual do vídeo."""
        parts = [f"🎬 Vídeo: {Path(video_path).name}"]

        if metadata.get("title"):
            parts.append(f"Título: {metadata['title']}")
        if metadata.get("duration"):
            mins = int(metadata["duration"]) // 60
            secs = int(metadata["duration"]) % 60
            parts.append(f"Duração: {mins}:{secs:02d}")
        if metadata.get("width") and metadata.get("height"):
            parts.append(f"Resolução: {metadata['width']}x{metadata['height']}")
        if metadata.get("video_codec"):
            parts.append(f"Codec: {metadata['video_codec']}")
        if metadata.get("has_audio"):
            parts.append(f"Áudio: {metadata.get('audio_codec', 'sim')} ({metadata.get('audio_sample_rate', '?')}Hz)")
        if metadata.get("uploader"):
            parts.append(f"Autor: {metadata['uploader']}")
        if metadata.get("description"):
            parts.append(f"\nDescrição: {metadata['description']}")

        parts.append(f"\n📸 {self.num_frames} frames extraídos | 🎵 Transcrição: {'sim' if self.transcribe_audio else 'não'}")

        return "\n".join(parts)
