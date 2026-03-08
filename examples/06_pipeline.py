"""Exemplo 06 — Pipeline de processamento de dados."""

import asyncio
from omniachain import (
    SequentialPipeline, ParallelPipeline,
    Context, CostTracker,
)


async def carregar_dados(ctx: Context) -> None:
    """Step 1: Carregar dados."""
    ctx.set("dados", {"vendas": [100, 200, 300], "custos": [50, 100, 150]})
    ctx.set("status", "dados carregados")


async def processar_vendas(ctx: Context) -> None:
    """Processamento paralelo — vendas."""
    dados = ctx.get("dados", {})
    total = sum(dados.get("vendas", []))
    ctx.set("total_vendas", total)


async def processar_custos(ctx: Context) -> None:
    """Processamento paralelo — custos."""
    dados = ctx.get("dados", {})
    total = sum(dados.get("custos", []))
    ctx.set("total_custos", total)


async def gerar_relatorio(ctx: Context) -> None:
    """Step final: Gerar relatório."""
    vars = ctx.variables
    vendas = vars.get("processar_vendas.total_vendas", 0) or vars.get("total_vendas", 0)
    custos = vars.get("processar_custos.total_custos", 0) or vars.get("total_custos", 0)

    relatorio = f"""
📊 RELATÓRIO FINANCEIRO
═══════════════════════
Total Vendas:  R${vendas:,.2f}
Total Custos:  R${custos:,.2f}
Lucro Líquido: R${(vendas - custos):,.2f}
Margem:        {((vendas - custos) / vendas * 100):.1f}%
"""
    ctx.set("relatorio", relatorio)


async def main():
    # Pipeline sequencial principal
    pipe = SequentialPipeline("analise-financeira")
    pipe.add(carregar_dados)

    # Processamento paralelo dentro do sequencial
    parallel = ParallelPipeline("processar-dados")
    parallel.add(processar_vendas)
    parallel.add(processar_custos)

    # Executar
    ctx = Context()
    await pipe.run(ctx)

    # Executar paralelo
    await parallel.run(ctx)

    # Gerar relatório
    await gerar_relatorio(ctx)

    print(ctx.get("relatorio"))


if __name__ == "__main__":
    asyncio.run(main())
