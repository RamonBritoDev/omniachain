"""
OmniaChain — ArtistAgent: agente especializado em gerar e editar imagens.

Exemplo::

    from omniachain import ArtistAgent, OpenAI

    artist = ArtistAgent(provider=OpenAI(), image_backend="openai")
    await artist.create("Um logo minimalista para café", "logo.png")

    # Com Google Nano Banana
    artist = ArtistAgent(provider=Google(), image_backend="google")
    await artist.create("Paisagem cyberpunk", "cidade.png")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from omniachain.agents.base import BaseAgent
from omniachain.media.image_gen import ImageGenerator
from omniachain.tools.base import Tool


ARTIST_PROMPT = """Você é um artista de IA especializado em gerar e editar imagens.

Quando o usuário pede para criar uma imagem, você deve:
1. Interpretar a descrição do usuário
2. Criar um prompt detalhado e otimizado para geração de imagens
3. Incluir detalhes de estilo, iluminação, composição, cores e técnica artística
4. Gerar a imagem

Quando o usuário pede para editar uma imagem existente, interprete a instrução \
e aplique as mudanças solicitadas.

Sempre responda em português, descrevendo o que foi gerado."""


class ArtistAgent(BaseAgent):
    """Agente especializado em gerar e editar imagens.

    Exemplo::

        artist = ArtistAgent(
            provider=OpenAI(),
            image_backend="openai",  # ou "google", "stability", "comfyui"
        )

        # Gerar imagem
        await artist.create("Um gato astronauta", "gato.png")

        # Editar imagem
        await artist.edit_image("gato.png", "Adicione um capacete", "gato_capacete.png")
    """

    def __init__(
        self,
        provider: Any = None,
        tools: Optional[list[Tool]] = None,
        name: str = "artist-agent",
        system_prompt: Optional[str] = None,
        image_backend: str = "auto",
        **kwargs: Any,
    ) -> None:
        # Extrair config do ImageGenerator antes de passar para super
        img_kwargs = {}
        for key in ["api_key", "base_url", "model"]:
            if key in kwargs:
                img_kwargs[key] = kwargs.pop(key)

        super().__init__(
            provider=provider,
            tools=tools,
            name=name,
            system_prompt=system_prompt or ARTIST_PROMPT,
            memory="buffer",
            **kwargs,
        )
        self.image_gen = ImageGenerator(backend=image_backend, **img_kwargs)

    async def create(
        self,
        description: str,
        output_path: Union[str, Path],
        optimize_prompt: bool = True,
        **kwargs: Any,
    ) -> Path:
        """Gera uma imagem a partir de uma descrição.

        Args:
            description: Descrição em linguagem natural.
            output_path: Caminho para salvar a imagem.
            optimize_prompt: Se True, usa o LLM para otimizar o prompt antes de gerar.

        Returns:
            Path do arquivo da imagem gerada.
        """
        if optimize_prompt:
            # Usar o LLM para criar um prompt otimizado
            response = await self.run(
                f"Crie um prompt detalhado em inglês para gerar a seguinte imagem. "
                f"Retorne APENAS o prompt otimizado, sem explicações:\n\n{description}"
            )
            prompt = response.content.strip().strip('"').strip("'")
        else:
            prompt = description

        return await self.image_gen.generate_to_file(prompt, output_path, **kwargs)

    async def create_variations(
        self,
        description: str,
        output_dir: Union[str, Path],
        n: int = 4,
        **kwargs: Any,
    ) -> list[Path]:
        """Gera múltiplas variações de uma imagem.

        Args:
            description: Descrição da imagem.
            output_dir: Diretório para salvar as imagens.
            n: Número de variações.

        Returns:
            Lista de Paths dos arquivos criados.
        """
        response = await self.run(
            f"Crie um prompt detalhado em inglês para gerar esta imagem. "
            f"Retorne APENAS o prompt:\n\n{description}"
        )
        prompt = response.content.strip().strip('"').strip("'")
        return await self.image_gen.generate_multiple(prompt, output_dir, n=n, **kwargs)

    async def edit_image(
        self,
        image_path: Union[str, Path],
        instruction: str,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> Path:
        """Edita uma imagem existente com base em instrução.

        Args:
            image_path: Caminho da imagem original.
            instruction: Instrução de edição em linguagem natural.
            output_path: Caminho de saída (padrão: sobrescreve original).

        Returns:
            Path do arquivo editado.
        """
        return await self.image_gen.edit_file(
            image_path, instruction, output_path=output_path, **kwargs
        )
