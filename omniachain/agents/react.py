"""
OmniaChain — ReActAgent: Reason + Act com tool calling.

Implementa o padrão ReAct: o agente raciocina, age (usa tools) e observa resultados.
"""

from __future__ import annotations

from typing import Any, Optional

from omniachain.agents.base import BaseAgent
from omniachain.providers.base import BaseProvider
from omniachain.security.keypair import KeyPair
from omniachain.security.permissions import Permissions
from omniachain.tools.base import Tool


REACT_SYSTEM_PROMPT = """Você é um agente de IA que segue o padrão ReAct (Reason + Act).

Para cada tarefa:
1. **Thought**: Pense sobre o que precisa fazer
2. **Action**: Use as tools disponíveis quando necessário
3. **Observation**: Observe o resultado da ação
4. **Repeat**: Continue até ter a resposta final

Responda de forma clara e precisa. Use tools quando precisar de informações externas ou cálculos."""


class ReActAgent(BaseAgent):
    """Agente ReAct — Reason + Act com tool calling.

    Exemplo::

        agent = ReActAgent(
            provider=Anthropic(),
            tools=[web_search, calculator],
            name="researcher"
        )
        result = await agent.run("Qual a população do Brasil dividida por 27?")
    """

    def __init__(
        self,
        provider: Any = None,
        tools: Optional[list[Tool]] = None,
        name: str = "react-agent",
        max_iterations: int = 15,
        system_prompt: Optional[str] = None,
        keypair: Optional[KeyPair] = None,
        permissions: Optional[Permissions] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            provider=provider,
            tools=tools,
            name=name,
            max_iterations=max_iterations,
            system_prompt=system_prompt or REACT_SYSTEM_PROMPT,
            keypair=keypair,
            permissions=permissions,
            memory="buffer",
            **kwargs,
        )
