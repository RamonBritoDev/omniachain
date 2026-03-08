"""Exemplo 02 — Análise multi-modal: PDF + imagem + CSV."""

import asyncio
from omniachain import MultimodalAgent, OpenAI


async def main():
    agent = MultimodalAgent(
        provider=OpenAI("gpt-4o"),
        name="analyst",
    )

    # Processar múltiplos tipos de arquivo
    result = await agent.run(
        "Analise todos os dados fornecidos e gere um resumo executivo",
        inputs=[
            "relatorio.pdf",
            "grafico_vendas.png",
            "dados_financeiros.csv",
        ],
    )

    print(result.content)
    print(f"\nTokens usados: {result.usage.total_tokens}")


if __name__ == "__main__":
    asyncio.run(main())
