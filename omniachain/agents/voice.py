"""
OmniaChain — VoiceAgent: agente que conversa via voz (STT → LLM → TTS).

Exemplo::

    from omniachain import VoiceAgent, OpenAI

    agent = VoiceAgent(provider=OpenAI())

    # Processar áudio e responder com áudio
    audio_resposta = await agent.listen_and_respond("pergunta.mp3")

    # Modo interativo no terminal (texto)
    await agent.chat()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from omniachain.agents.base import BaseAgent
from omniachain.media.stt import SpeechToText
from omniachain.media.tts import TextToSpeech
from omniachain.tools.base import Tool


VOICE_PROMPT = """Você é um assistente de IA com voz. Você recebe áudio transcrito do usuário \
e responde de forma natural e conversacional. Seja claro e conciso nas respostas, \
pois elas serão convertidas em áudio. Evite listas longas ou formatação complexa."""


class VoiceAgent(BaseAgent):
    """Agente que conversa via voz: STT → LLM → TTS.

    Exemplo::

        agent = VoiceAgent(
            provider=OpenAI(),
            stt_backend="whisper-local",
            tts_backend="edge",
            tts_voice="pt-BR-AntonioNeural",
        )

        # Processar áudio
        audio = await agent.listen_and_respond("pergunta.mp3")

        # Modo interativo texto
        await agent.chat()
    """

    def __init__(
        self,
        provider: Any = None,
        tools: Optional[list[Tool]] = None,
        name: str = "voice-agent",
        system_prompt: Optional[str] = None,
        stt_backend: str = "auto",
        tts_backend: str = "auto",
        tts_voice: Optional[str] = None,
        language: str = "pt",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            provider=provider,
            tools=tools,
            name=name,
            system_prompt=system_prompt or VOICE_PROMPT,
            memory="buffer",
            **kwargs,
        )
        self.stt = SpeechToText(backend=stt_backend, language=language)
        self.tts = TextToSpeech(backend=tts_backend, voice=tts_voice, language=language)

    async def listen_and_respond(
        self,
        audio_source: Union[str, Path, bytes],
        output_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> bytes:
        """Recebe áudio, transcreve, processa e responde com áudio.

        Args:
            audio_source: Caminho de arquivo de áudio ou bytes.
            output_path: Se fornecido, salva o áudio de resposta neste caminho.

        Returns:
            Bytes do áudio da resposta.
        """
        # 1. STT — Transcrever áudio
        texto_usuario = await self.stt.transcribe(audio_source)

        # 2. LLM — Processar com o agente
        response = await self.run(texto_usuario, **kwargs)

        # 3. TTS — Sintetizar resposta
        if output_path:
            await self.tts.speak_to_file(response.content, output_path)

        return await self.tts.speak(response.content)

    async def listen_and_respond_text(
        self, audio_source: Union[str, Path, bytes], **kwargs: Any
    ) -> str:
        """Recebe áudio, transcreve e responde com texto (sem TTS).

        Útil para obter a resposta em texto antes de sintetizar.
        """
        texto_usuario = await self.stt.transcribe(audio_source)
        response = await self.run(texto_usuario, **kwargs)
        return response.content

    async def chat(self) -> None:
        """Modo interativo no terminal (input/output texto).

        O usuário digita, o agente responde. Ctrl+C para sair.
        """
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        console.print(Panel(
            "[bold green]🎙️ VoiceAgent — Modo Interativo[/]"
            "\n\nDigite suas mensagens. Ctrl+C para sair.",
            border_style="green",
        ))

        try:
            while True:
                user_input = console.input("\n[bold cyan]Você:[/] ")
                if not user_input.strip():
                    continue

                console.print("[dim]Pensando...[/]", end="")
                response = await self.run(user_input)
                console.print(f"\r[bold green]🤖 Agente:[/] {response.content}")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Conversa encerrada.[/]")
