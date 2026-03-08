"""Exemplo 03 — Sessão multi-agente com Supervisor."""

import asyncio
from omniachain import (
    Anthropic, Groq, OpenAI,
    ReActAgent, PlannerAgent, SupervisorAgent,
    Session, web_search, calculator, file_write,
)


async def main():
    # Criar agentes especializados
    researcher = ReActAgent(
        provider=Anthropic(),
        tools=[web_search],
        name="researcher",
    )

    analyst = PlannerAgent(
        provider=OpenAI("gpt-4o"),
        tools=[calculator],
        name="analyst",
    )

    writer = ReActAgent(
        provider=Groq(),
        tools=[file_write],
        name="writer",
    )

    # Supervisor coordena os agentes
    supervisor = SupervisorAgent(
        provider=Anthropic(),
        sub_agents=[researcher, analyst, writer],
    )

    result = await supervisor.run(
        "Pesquise as tendências de IA em 2025, analise os dados e escreva um relatório"
    )

    print(result.content)
    print(f"\nAgentes usados: {result.metadata.get('agents_used', [])}")
    print(f"Custo total: ${result.usage.cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
