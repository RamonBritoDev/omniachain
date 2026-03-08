"""OmniaChain — SupervisorAgent: coordena múltiplos agentes."""

from __future__ import annotations

from typing import Any, Optional

from omniachain.agents.base import BaseAgent
from omniachain.core.message import Message
from omniachain.core.response import Response, Usage
from omniachain.tools.base import Tool


SUPERVISOR_PROMPT = """Você é um supervisor que coordena uma equipe de agentes especializados.

Agentes disponíveis:
{agents}

Para cada tarefa:
1. Analise o que precisa ser feito
2. Delegue sub-tarefas para os agentes mais apropriados
3. Combine os resultados em uma resposta final coerente

Responda com as delegações no formato:
DELEGATE: [nome_agente] -> [tarefa]"""


class SupervisorAgent(BaseAgent):
    """Agente supervisor que coordena múltiplos agentes.

    Exemplo::

        supervisor = SupervisorAgent(
            provider=Anthropic(),
            sub_agents=[researcher, analyst, writer],
        )
        result = await supervisor.run("Pesquise, analise e escreva sobre IA")
    """

    def __init__(
        self,
        provider: Any = None,
        sub_agents: Optional[list[BaseAgent]] = None,
        name: str = "supervisor",
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.sub_agents = sub_agents or []
        agents_desc = "\n".join(
            f"- {a.name}: {a.system_prompt[:100]}..."
            for a in self.sub_agents
        )
        prompt = (system_prompt or SUPERVISOR_PROMPT).format(agents=agents_desc)

        super().__init__(
            provider=provider,
            name=name,
            system_prompt=prompt,
            memory="summary",
            **kwargs,
        )

    async def run(
        self,
        prompt: str,
        inputs: Optional[list[Any]] = None,
        **kwargs: Any,
    ) -> Response:
        """Executa o supervisor: analisa, delega e combina."""
        provider = self._resolved_provider or self.provider_instance
        if not provider:
            from omniachain.core.errors import OmniaError
            raise OmniaError("Nenhum provider configurado.", suggestion="Passe provider=...")

        total_usage = Usage()

        # Step 1: Supervisor analisa e planeja delegações
        analysis_response = await provider.complete(
            [Message.system(self.system_prompt), Message.user(prompt)]
        )
        total_usage = total_usage + analysis_response.usage

        # Step 2: Extrair delegações e executar sub-agentes
        results: dict[str, str] = {}
        delegations = self._parse_delegations(analysis_response.content)

        if delegations:
            for agent_name, task in delegations.items():
                agent = self._find_agent(agent_name)
                if agent:
                    try:
                        sub_response = await agent.run(task, inputs=inputs)
                        results[agent_name] = sub_response.content
                        total_usage = total_usage + sub_response.usage
                    except Exception as e:
                        results[agent_name] = f"Erro: {e}"
        else:
            # Se não delega, usa o próprio resultado
            results["supervisor"] = analysis_response.content

        # Step 3: Combinar resultados
        if len(results) > 1:
            combine_prompt = f"Combine os seguintes resultados dos agentes em uma resposta coerente:\n\n"
            for name, result in results.items():
                combine_prompt += f"## {name}\n{result[:1000]}\n\n"
            combine_prompt += f"\nObjetivo original: {prompt}"

            final = await provider.complete(
                [Message.system("Combine os resultados de forma clara e coerente."),
                 Message.user(combine_prompt)]
            )
            total_usage = total_usage + final.usage
            content = final.content
        else:
            content = list(results.values())[0] if results else analysis_response.content

        response = Response(
            content=content,
            provider=provider.provider_name,
            model=provider.model,
            usage=total_usage,
            metadata={
                "agents_used": list(results.keys()),
                "delegations": delegations,
            },
        )
        return response

    def _parse_delegations(self, text: str) -> dict[str, str]:
        """Extrai delegações do formato DELEGATE: agent -> task."""
        delegations: dict[str, str] = {}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("DELEGATE:"):
                parts = line.replace("DELEGATE:", "").strip()
                if "->" in parts:
                    agent, task = parts.split("->", 1)
                    delegations[agent.strip()] = task.strip()
        return delegations

    def _find_agent(self, name: str) -> Optional[BaseAgent]:
        """Encontra um sub-agente por nome."""
        for agent in self.sub_agents:
            if agent.name.lower() == name.lower():
                return agent
        return None
