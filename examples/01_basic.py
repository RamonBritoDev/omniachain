"""Exemplo 01 — Uso básico sem boilerplate."""

import asyncio
from omniachain import Agent, Anthropic, calculator, web_search


async def main():
    # Criar agente com uma linha
    agent = Agent(
        provider=Anthropic(),
        tools=[calculator, web_search],
    )

    # Fazer pergunta
    result = await agent.run("Quanto é 1547 * 32 + raiz quadrada de 144?")
    print(f"Resposta: {result.content}")
    print(f"Tokens: {result.usage.total_tokens}")
    print(f"Custo: ${result.usage.cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
