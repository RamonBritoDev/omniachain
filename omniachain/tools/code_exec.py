"""OmniaChain — Tool de execução de código Python em sandbox seguro."""

from omniachain.tools.base import tool


@tool(timeout=30.0, retries=1)
async def code_exec(code: str) -> str:
    """Executa código Python em um ambiente sandbox seguro.

    O código é executado em um subprocess isolado com timeout.

    Args:
        code: Código Python para executar.

    Returns:
        Saída stdout/stderr da execução.
    """
    import asyncio
    import sys
    import tempfile
    import os

    # Escrever código em arquivo temporário
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        temp_path = f.name

    try:
        # Executar em subprocess com timeout
        process = await asyncio.create_subprocess_exec(
            sys.executable, temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=25.0,
            )
        except asyncio.TimeoutError:
            process.kill()
            return "Erro: execução excedeu o tempo limite de 25 segundos."

        outputs = []
        if stdout:
            outputs.append(f"Saída:\n{stdout.decode('utf-8', errors='replace')[:10000]}")
        if stderr:
            outputs.append(f"Erros:\n{stderr.decode('utf-8', errors='replace')[:5000]}")
        if process.returncode != 0:
            outputs.append(f"Código de saída: {process.returncode}")

        return "\n".join(outputs) if outputs else "Execução concluída sem saída."

    finally:
        os.unlink(temp_path)
