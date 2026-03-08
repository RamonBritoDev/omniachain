"""OmniaChain — Tool de geração de imagens para agentes."""

from omniachain.tools.base import tool


@tool(timeout=120.0, description="Gera uma imagem a partir de um prompt de texto.")
async def generate_image(
    prompt: str,
    output_path: str = "output.png",
    size: str = "1024x1024",
    backend: str = "auto",
) -> str:
    """Gera uma imagem a partir de descrição textual.

    Args:
        prompt: Descrição da imagem a gerar.
        output_path: Caminho do arquivo de saída (.png)
        size: Dimensões da imagem (ex: 1024x1024, 1792x1024)
        backend: Backend de geração (auto, openai, google, stability, comfyui)
    """
    from omniachain.media.image_gen import ImageGenerator

    gen = ImageGenerator(backend=backend)
    path = await gen.generate_to_file(prompt, output_path, size=size)
    return f"Imagem gerada e salva em: {path}"
