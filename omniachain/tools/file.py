"""OmniaChain — Tools de manipulação de arquivos."""

import aiofiles

from omniachain.tools.base import tool


@tool(timeout=10.0)
async def file_read(path: str) -> str:
    """Lê o conteúdo de um arquivo.

    Args:
        path: Caminho do arquivo para ler.

    Returns:
        Conteúdo do arquivo como string.
    """
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()
    return content[:50000]  # Limitar para evitar overflow


@tool(timeout=10.0)
async def file_write(path: str, content: str) -> str:
    """Escreve conteúdo em um arquivo.

    Args:
        path: Caminho do arquivo para escrever.
        content: Conteúdo para escrever.

    Returns:
        Confirmação da escrita.
    """
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)
    return f"Arquivo salvo: {path} ({len(content)} caracteres)"


@tool(timeout=10.0)
async def file_list(directory: str) -> str:
    """Lista arquivos e diretórios em um diretório.

    Args:
        directory: Caminho do diretório.

    Returns:
        Lista de arquivos e diretórios.
    """
    import os

    entries = []
    for entry in os.scandir(directory):
        tipo = "📁" if entry.is_dir() else "📄"
        size = ""
        if entry.is_file():
            stat = entry.stat()
            size = f" ({stat.st_size:,} bytes)"
        entries.append(f"{tipo} {entry.name}{size}")

    if not entries:
        return f"Diretório vazio: {directory}"

    return f"Conteúdo de {directory}:\n" + "\n".join(sorted(entries))
