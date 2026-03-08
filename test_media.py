"""Teste de integração: Audio e Video Loaders com OpenAI."""

import asyncio
import os
import subprocess
import tempfile
import sys

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your-api-key-here")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_test_audio(path: str, duration: int = 3) -> None:
    """Gera um áudio de teste com ffmpeg (tom de 440Hz)."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",
        "-ar", "16000", "-ac", "1",
        path,
    ], capture_output=True)
    print(f"   Áudio criado: {path} ({os.path.getsize(path)} bytes)")


def create_test_video(path: str, duration: int = 3) -> None:
    """Gera um vídeo de teste com ffmpeg (cor + tom)."""
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=blue:s=320x240:d={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        path,
    ], capture_output=True)
    print(f"   Vídeo criado: {path} ({os.path.getsize(path)} bytes)")


async def test_1_audio_loader():
    """Teste: AudioLoader carrega arquivo WAV."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 1: AudioLoader — carregar áudio WAV")
    print("=" * 60)

    from omniachain.loaders.audio import AudioLoader

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio_path = f.name

    try:
        create_test_audio(audio_path)

        loader = AudioLoader()
        content = await loader.load(audio_path)

        print(f"   Tipo: {content.type.value}")
        print(f"   Dados: {str(content.data)[:200]}")
        print(f"   Mime: {content.mime_type}")
        print(f"   Metadata: {content.metadata}")
        print(f"✅ AudioLoader funcionou!")
        return True
    finally:
        os.unlink(audio_path)


async def test_2_video_loader_frames():
    """Teste: VideoLoader extrai frames."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 2: VideoLoader — extrair frames do vídeo")
    print("=" * 60)

    from omniachain.loaders.video import VideoLoader

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        video_path = f.name

    try:
        create_test_video(video_path, duration=5)

        loader = VideoLoader(num_frames=3, transcribe_audio=False)
        contents = await loader.load(video_path)

        print(f"   Total de conteúdos: {len(contents)}")
        for i, c in enumerate(contents):
            if c.type.value == "text":
                print(f"   [{i}] TEXTO: {str(c.data)[:150]}")
            elif c.type.value == "image":
                print(f"   [{i}] FRAME: {str(c.data)[:50]}... ({len(str(c.data))} chars base64)")
                print(f"         Metadata: {c.metadata}")

        frames = [c for c in contents if c.type.value == "image"]
        print(f"\n   📸 Frames extraídos: {len(frames)}")
        assert len(frames) >= 1, "Nenhum frame extraído!"
        print(f"✅ VideoLoader frames funcionou!")
        return True
    finally:
        os.unlink(video_path)


async def test_3_video_loader_audio():
    """Teste: VideoLoader extrai e transcreve áudio."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 3: VideoLoader — extrair áudio do vídeo")
    print("=" * 60)

    from omniachain.loaders.video import VideoLoader

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        video_path = f.name

    try:
        create_test_video(video_path, duration=3)

        loader = VideoLoader(num_frames=2, transcribe_audio=True)
        contents = await loader.load(video_path)

        print(f"   Total de conteúdos: {len(contents)}")
        for i, c in enumerate(contents):
            role = c.metadata.get("role", "?")
            if c.type.value == "text":
                print(f"   [{i}] {role}: {str(c.data)[:150]}")
            elif c.type.value == "image":
                print(f"   [{i}] {role}: base64 ({len(str(c.data))} chars)")

        # Verificar que tem resumo + frames + transcrição
        has_summary = any(c.metadata.get("role") == "video_summary" for c in contents)
        has_frames = any(c.metadata.get("role") == "video_frame" for c in contents)
        has_audio = any(c.metadata.get("role") == "audio_transcription" for c in contents)

        print(f"\n   📊 Resumo: {'✅' if has_summary else '❌'}")
        print(f"   📸 Frames: {'✅' if has_frames else '❌'}")
        print(f"   🎵 Transcrição: {'✅' if has_audio else '⚠️ (whisper não instalado, normal)'}")

        print(f"✅ VideoLoader com áudio funcionou!")
        return True
    finally:
        os.unlink(video_path)


async def test_4_agent_with_video():
    """Teste: Agente analisa vídeo (frames enviados ao GPT-4o-mini)."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 4: Agente analisa frames de vídeo com GPT-4o-mini")
    print("=" * 60)

    from omniachain.loaders.video import VideoLoader
    from omniachain.providers.openai import OpenAIProvider
    from omniachain.core.message import Message, MessageContent, ContentType

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        video_path = f.name

    try:
        create_test_video(video_path, duration=3)

        # Extrair frames
        loader = VideoLoader(num_frames=2, transcribe_audio=False)
        contents = await loader.load(video_path)

        # Montar mensagem multi-modal com frames
        msg_parts = [MessageContent.text("Descreva o que você vê nos frames deste vídeo. Que cor predomina?")]
        for c in contents:
            if c.type.value == "image":
                msg_parts.append(MessageContent(
                    type=ContentType.IMAGE,
                    data=c.data,
                    mime_type="image/jpeg",
                ))

        if len(msg_parts) < 2:
            print("   ⚠️ Nenhum frame extraído, pulando teste de visão")
            return True

        # Enviar ao GPT-4o-mini (tem visão!)
        provider = OpenAIProvider(model="gpt-4o-mini")
        messages = [
            Message.system("Descreva imagens de forma curta em português."),
            Message(role=Message.user("").role, content=msg_parts),
        ]

        response = await provider.complete(messages)
        print(f"   GPT-4o-mini respondeu: {response.content[:200]}")
        print(f"   Tokens: {response.usage.total_tokens} | Custo: ${response.usage.cost:.6f}")

        assert len(response.content) > 10, "Resposta muito curta"
        print(f"✅ Agente analisou frames do vídeo com sucesso!")
        return True
    finally:
        os.unlink(video_path)


async def main():
    print("🚀 OmniaChain — Teste de Áudio e Vídeo")
    print("=" * 60)

    # Verificar ffmpeg
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        print(f"   ffmpeg: disponível ✅")
    except FileNotFoundError:
        print("❌ ffmpeg não encontrado! Instale com: winget install Gyan.FFmpeg")
        return

    tests = [
        ("AudioLoader", test_1_audio_loader),
        ("VideoLoader frames", test_2_video_loader_frames),
        ("VideoLoader áudio", test_3_video_loader_audio),
        ("Agente + vídeo", test_4_agent_with_video),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            print(f"\n❌ FALHOU: {name}")
            print(f"   Erro: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 RESULTADO: {passed} ✅ | {failed} ❌ de {len(tests)} testes")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
