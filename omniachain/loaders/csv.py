"""OmniaChain — Loader de dados tabulares (.csv, .xlsx)."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from omniachain.core.errors import LoaderError
from omniachain.core.message import ContentType, MessageContent
from omniachain.loaders.base import BaseLoader


class CSVLoader(BaseLoader):
    """Carrega dados tabulares de CSV e Excel.

    Exemplo::

        loader = CSVLoader()
        content = await loader.load("dados.csv")
        print(content.data)  # Representação tabular dos dados
    """

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".tsv"}

    def __init__(self, max_rows: int = 1000, include_stats: bool = True) -> None:
        self.max_rows = max_rows
        self.include_stats = include_stats

    async def load(self, source: Union[str, Path, bytes]) -> MessageContent:
        """Carrega dados tabulares e retorna como texto formatado."""
        try:
            import pandas as pd
            import asyncio
            import io

            if isinstance(source, bytes):
                df = await asyncio.to_thread(pd.read_csv, io.BytesIO(source))
                metadata: dict = {}
            else:
                path = Path(str(source))
                ext = path.suffix.lower()
                metadata = self._get_metadata(path)

                if ext in (".xlsx", ".xls"):
                    df = await asyncio.to_thread(pd.read_excel, str(path))
                elif ext == ".tsv":
                    df = await asyncio.to_thread(pd.read_csv, str(path), sep="\t")
                else:
                    df = await asyncio.to_thread(pd.read_csv, str(path))

            # Truncar se necessário
            truncated = len(df) > self.max_rows
            if truncated:
                df_display = df.head(self.max_rows)
            else:
                df_display = df

            # Montar texto
            parts: list[str] = []
            parts.append(f"Dados tabulares: {len(df)} linhas × {len(df.columns)} colunas")
            parts.append(f"Colunas: {', '.join(df.columns.tolist())}")

            if self.include_stats:
                parts.append("\n--- Estatísticas ---")
                parts.append(df.describe(include="all").to_string())

            parts.append("\n--- Dados ---")
            parts.append(df_display.to_string(index=False))

            if truncated:
                parts.append(f"\n[... truncado: mostrando {self.max_rows} de {len(df)} linhas]")

            text = "\n".join(parts)

            metadata.update({
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "truncated": truncated,
            })

            return MessageContent(
                type=ContentType.TABLE,
                data=text,
                metadata=metadata,
            )

        except ImportError:
            raise LoaderError(
                "Pacote 'pandas' não instalado.",
                loader="CSVLoader",
                source=str(source),
                suggestion="Instale com: pip install pandas openpyxl",
            )
        except Exception as e:
            raise LoaderError(
                f"Erro ao carregar dados tabulares: {e}",
                loader="CSVLoader",
                source=str(source),
                original_error=e,
            )
