"""OmniaChain — Dashboard local opcional (Rich terminal)."""

from __future__ import annotations

from typing import Any, Optional

from omniachain.observability.costs import CostTracker
from omniachain.observability.tracer import Tracer


class Dashboard:
    """Dashboard local no terminal usando Rich.

    Exemplo::

        dashboard = Dashboard(cost_tracker=tracker, tracer=tracer)
        dashboard.show()
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None, tracer: Optional[Tracer] = None) -> None:
        self.cost_tracker = cost_tracker or CostTracker()
        self.tracer = tracer or Tracer()

    def show(self) -> None:
        """Exibe dashboard no terminal."""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel

            console = Console()

            # Custos
            console.print(Panel(self.cost_tracker.summary(), title="💰 Custos", border_style="green"))

            # Traces
            traces = self.tracer.get_traces(limit=10)
            if traces:
                table = Table(title="🔍 Últimos Traces")
                table.add_column("Trace ID", style="cyan")
                table.add_column("Spans", style="magenta")
                table.add_column("Duração", style="yellow")

                for trace in traces:
                    total_ms = sum(s.duration_ms for s in trace.spans)
                    table.add_row(trace.trace_id, str(len(trace.spans)), f"{total_ms:.1f}ms")

                console.print(table)

            # Custos por provider
            by_prov = self.cost_tracker.by_provider()
            if by_prov:
                table2 = Table(title="📊 Custos por Provider")
                table2.add_column("Provider", style="cyan")
                table2.add_column("Custo", style="green")
                table2.add_column("Tokens", style="yellow")
                table2.add_column("Chamadas", style="magenta")

                for prov, data in by_prov.items():
                    table2.add_row(prov, f"${data['cost']:.4f}", f"{data['tokens']:,}", str(data["calls"]))

                console.print(table2)

        except ImportError:
            # Fallback sem Rich
            print(self.cost_tracker.summary())
            print(f"\nTraces: {len(self.tracer.get_traces())}")

    def show_trace(self, trace_id: str) -> None:
        """Exibe detalhes de um trace específico."""
        traces = [t for t in self.tracer.get_traces() if t.trace_id == trace_id]
        if not traces:
            print(f"Trace {trace_id} não encontrado.")
            return

        trace = traces[0]
        print(f"\n═══ Trace: {trace.trace_id} ═══")
        for span in trace.spans:
            status = "✅" if span.status == "ok" else "❌"
            print(f"  {status} {span.name} ({span.duration_ms:.1f}ms)")
            for k, v in span.attributes.items():
                print(f"     {k}: {v}")
