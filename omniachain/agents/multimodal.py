"""OmniaChain — MultimodalAgent: processa qualquer tipo de input."""

from __future__ import annotations

from typing import Any, Optional

from omniachain.agents.base import BaseAgent
from omniachain.tools.base import Tool


MULTIMODAL_PROMPT = """Você é um agente de IA multimodal capaz de processar e analisar:
- Texto e documentos
- Imagens e fotos
- Dados tabulares (CSV, Excel)
- Código fonte
- Áudio e vídeo (via transcrição)
- URLs e páginas web

Analise todos os inputs fornecidos e responda de forma completa e precisa."""


class MultimodalAgent(BaseAgent):
    """Agente que processa qualquer tipo de input multi-modal.

    Exemplo::

        agent = MultimodalAgent(provider=OpenAI("gpt-4o"))
        result = await agent.run(
            "Analise estes dados",
            inputs=["relatorio.pdf", "grafico.png", "dados.csv"]
        )
    """

    def __init__(
        self,
        provider: Any = None,
        tools: Optional[list[Tool]] = None,
        name: str = "multimodal-agent",
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            provider=provider,
            tools=tools,
            name=name,
            system_prompt=system_prompt or MULTIMODAL_PROMPT,
            memory="buffer",
            **kwargs,
        )
