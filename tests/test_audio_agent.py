"""Teste interativo: Áudio → STT → Agente → Chat no terminal."""
import asyncio
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    audio_path = os.path.join(os.path.dirname(__file__), "WhatsApp Ptt 2026-03-07 at 22.51.19.ogg")

    print("=" * 60)
    print("🧪 OmniaChain — Agente Interativo com Áudio")
    print("=" * 60)

    # 1. Transcrever áudio direto via OpenAI (suporta ogg)
    print("\n🎙️ Transcrevendo áudio...")
    client = openai.AsyncOpenAI(api_key=api_key)

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    audio_file = io.BytesIO(audio_data)
    audio_file.name = "audio.ogg"

    transcript = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="pt",
    )
    texto = transcript.text
    print(f"📝 Transcrição: {texto}")

    # 2. Criar agente OmniaChain
    from omniachain.providers.openai import OpenAIProvider
    from omniachain.agents.base import BaseAgent

    provider = OpenAIProvider("gpt-4o-mini")
    agent = BaseAgent(
        provider=provider,
        name="audio-agent",
        system_prompt="Você é um assistente útil. Responda de forma clara e direta em português.",
        memory="buffer",
    )

    # 3. Primeira resposta (baseada no áudio)
    print("\n🤖 Processando...")
    response = await agent.run(texto)
    print(f"\n💬 Agente: {response.content}")

    # 4. Chat interativo
    print("\n" + "-" * 60)
    print("💡 Continue a conversa. Digite 'sair' para encerrar.")
    print("-" * 60)

    while True:
        try:
            user_input = input("\n🧑 Você: ")
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("sair", "exit", "quit"):
            break

        response = await agent.run(user_input)
        print(f"\n🤖 Agente: {response.content}")

    print("\n👋 Conversa encerrada!")


if __name__ == "__main__":
    asyncio.run(main())
