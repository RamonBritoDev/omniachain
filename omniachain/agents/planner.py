"""OmniaChain — PlannerAgent: Plan → Execute → Review."""

from __future__ import annotations

from typing import Any, Optional

from omniachain.agents.base import BaseAgent
from omniachain.core.message import Message
from omniachain.core.response import Response, Usage
from omniachain.tools.base import Tool


PLANNER_PROMPT = """Você é um agente de planejamento que segue a metodologia Plan → Execute → Review.

Para cada tarefa:
1. **Plan**: Elabore um plano detalhado com steps numerados
2. **Execute**: Execute cada step do plano usando as tools disponíveis
3. **Review**: Revise o resultado e verifique se atende ao objetivo

Se o resultado não for satisfatório, refine o plano e tente novamente."""


class PlannerAgent(BaseAgent):
    """Agente que planeja antes de executar: Plan → Execute → Review.

    Exemplo::

        agent = PlannerAgent(
            provider=Anthropic(),
            tools=[web_search, file],
            name="planner"
        )
        result = await agent.run("Crie um relatório sobre tendências de IA")
    """

    def __init__(
        self,
        provider: Any = None,
        tools: Optional[list[Tool]] = None,
        name: str = "planner-agent",
        max_iterations: int = 20,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            provider=provider,
            tools=tools,
            name=name,
            max_iterations=max_iterations,
            system_prompt=system_prompt or PLANNER_PROMPT,
            memory="summary",
            **kwargs,
        )

    async def run(
        self,
        prompt: str,
        inputs: Optional[list[Any]] = None,
        **kwargs: Any,
    ) -> Response:
        """Executa com ciclo Plan → Execute → Review."""
        provider = self._resolved_provider or self.provider_instance
        if not provider:
            from omniachain.core.errors import OmniaError
            raise OmniaError("Nenhum provider configurado.", suggestion="Passe provider=...")

        total_usage = Usage()

        # Step 1: Plan
        plan_prompt = f"Crie um plano detalhado para: {prompt}\n\nListe os steps numerados."
        plan_response = await provider.complete(
            [Message.system(self.system_prompt), Message.user(plan_prompt)]
        )
        total_usage = total_usage + plan_response.usage
        plan = plan_response.content

        # Step 2: Execute (usando o run do BaseAgent)
        execute_prompt = f"Execute o seguinte plano:\n\n{plan}\n\nTarefa original: {prompt}"
        response = await super().run(execute_prompt, inputs=inputs, **kwargs)
        total_usage = total_usage + response.usage

        # Step 3: Review
        review_prompt = f"Revise o resultado: {response.content[:2000]}\n\nO objetivo era: {prompt}\n\nO resultado está completo e correto? Se não, o que falta?"
        review_response = await provider.complete(
            [Message.system("Seja um revisor crítico."), Message.user(review_prompt)]
        )
        total_usage = total_usage + review_response.usage

        # Montar resposta final
        response.content = response.content
        response.usage = total_usage
        response.metadata["plan"] = plan[:500]
        response.metadata["review"] = review_response.content[:500]

        return response
