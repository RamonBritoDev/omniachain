"""
OmniaChain — Geração de imagens com backends plugáveis.

Suporta APIs (OpenAI DALL-E, Google Nano Banana, Stability AI) e locais (ComfyUI).
Qualquer API pode ser conectada via register_backend().

Exemplo::

    from omniachain.media import ImageGenerator

    # DALL-E 3
    gen = ImageGenerator(backend="openai")
    await gen.generate_to_file("Um gato astronauta", "gato.png")

    # Google Nano Banana (Gemini Image)
    gen = ImageGenerator(backend="google")
    await gen.generate_to_file("Paisagem cyberpunk", "cidade.png")

    # Stable Diffusion local via ComfyUI
    gen = ImageGenerator(backend="comfyui", base_url="http://localhost:8188")
    await gen.generate_to_file("Retrato anime", "anime.png")

    # Qualquer API customizada
    ImageGenerator.register_backend("midjourney", MidjourneyBackend)
"""

from __future__ import annotations

import abc
import base64
import os
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from omniachain.core.errors import OmniaError


class GeneratedImage(BaseModel):
    """Uma imagem gerada."""
    data: bytes = b""
    format: str = "png"
    width: int = 0
    height: int = 0
    prompt: str = ""
    revised_prompt: str = ""
    backend_used: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class ImageBackend(abc.ABC):
    """Classe base abstrata para backends de geração de imagens.

    Para conectar qualquer API de geração de imagens::

        class MidjourneyBackend(ImageBackend):
            async def generate(self, prompt, size="1024x1024", n=1, **kw):
                # chamar API do Midjourney aqui
                return [image_bytes]

        ImageGenerator.register_backend("midjourney", MidjourneyBackend)
        gen = ImageGenerator(backend="midjourney")
    """

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs

    @abc.abstractmethod
    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
        **kwargs: Any,
    ) -> list[bytes]:
        """Gera imagem(ns) a partir de um prompt.

        Args:
            prompt: Descrição da imagem.
            size: Dimensões (ex: "1024x1024", "1792x1024").
            n: Número de imagens a gerar.

        Returns:
            Lista de bytes de imagens geradas.
        """
        ...

    async def edit(
        self,
        image: bytes,
        prompt: str,
        **kwargs: Any,
    ) -> bytes:
        """Edita uma imagem existente com base em um prompt.

        Nem todos os backends suportam edição.
        """
        raise OmniaError(
            f"O backend não suporta edição de imagens.",
            suggestion="Use um backend que suporte edição, como 'openai' ou 'google'.",
        )


# ──────────────────────────────────────────────
# Backends built-in
# ──────────────────────────────────────────────

class OpenAIImageBackend(ImageBackend):
    """Backend de geração de imagens via OpenAI DALL-E 3."""

    async def generate(
        self, prompt: str, size: str = "1024x1024", n: int = 1, **kwargs: Any
    ) -> list[bytes]:
        import openai

        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise OmniaError(
                "OPENAI_API_KEY não configurada para geração de imagens.",
                suggestion="Defina OPENAI_API_KEY ou passe api_key= no construtor.",
            )

        client = openai.AsyncOpenAI(api_key=api_key)
        model = self.config.get("model", "dall-e-3")
        quality = self.config.get("quality", "standard")
        style = self.config.get("style", "vivid")

        images: list[bytes] = []
        # DALL-E 3 suporta n=1 por vez
        for _ in range(n):
            response = await client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                response_format="b64_json",
                n=1,
                **kwargs,
            )
            b64_data = response.data[0].b64_json
            if b64_data:
                images.append(base64.b64decode(b64_data))

        return images

    async def edit(self, image: bytes, prompt: str, **kwargs: Any) -> bytes:
        import openai

        api_key = self.config.get("api_key") or os.getenv("OPENAI_API_KEY")
        client = openai.AsyncOpenAI(api_key=api_key)

        import io
        image_file = io.BytesIO(image)
        image_file.name = "image.png"

        response = await client.images.edit(
            model="dall-e-2",
            image=image_file,
            prompt=prompt,
            response_format="b64_json",
            n=1,
            **kwargs,
        )
        b64_data = response.data[0].b64_json
        return base64.b64decode(b64_data) if b64_data else b""


class GoogleImageBackend(ImageBackend):
    """Backend de geração de imagens via Google Gemini (Nano Banana).

    Usa a API Gemini para geração de imagens nativa.
    Modelos: gemini-2.0-flash (Nano Banana), gemini-2.5-flash-preview-image-generation.
    """

    async def generate(
        self, prompt: str, size: str = "1024x1024", n: int = 1, **kwargs: Any
    ) -> list[bytes]:
        import asyncio

        try:
            import google.generativeai as genai
        except ImportError:
            raise OmniaError(
                "Google Generative AI não instalado.",
                suggestion="Instale com: pip install google-generativeai",
            )

        api_key = self.config.get("api_key") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise OmniaError(
                "GOOGLE_API_KEY não configurada para geração de imagens.",
                suggestion="Defina GOOGLE_API_KEY ou passe api_key= no construtor.",
            )

        genai.configure(api_key=api_key)
        model_name = self.config.get("model", "gemini-2.0-flash-exp-image-generation")
        model = genai.GenerativeModel(model_name)

        images: list[bytes] = []
        for _ in range(n):
            result = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )
            # Extrair imagens da resposta
            for part in result.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    images.append(part.inline_data.data)

        return images

    async def edit(self, image: bytes, prompt: str, **kwargs: Any) -> bytes:
        import asyncio

        try:
            import google.generativeai as genai
        except ImportError:
            raise OmniaError(
                "Google Generative AI não instalado.",
                suggestion="Instale com: pip install google-generativeai",
            )

        api_key = self.config.get("api_key") or os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        model_name = self.config.get("model", "gemini-2.0-flash-exp-image-generation")
        model = genai.GenerativeModel(model_name)

        import PIL.Image
        import io

        img = PIL.Image.open(io.BytesIO(image))

        result = await asyncio.to_thread(
            model.generate_content,
            [prompt, img],
            generation_config=genai.GenerationConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in result.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                return part.inline_data.data

        return b""


class StabilityImageBackend(ImageBackend):
    """Backend via Stability AI (SDXL, SD3)."""

    async def generate(
        self, prompt: str, size: str = "1024x1024", n: int = 1, **kwargs: Any
    ) -> list[bytes]:
        import httpx

        api_key = self.config.get("api_key") or os.getenv("STABILITY_API_KEY")
        if not api_key:
            raise OmniaError(
                "STABILITY_API_KEY não configurada.",
                suggestion="Defina STABILITY_API_KEY ou passe api_key= no construtor.",
            )

        w, h = size.split("x")
        engine = self.config.get("model", "stable-diffusion-xl-1024-v1-0")

        images: list[bytes] = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"https://api.stability.ai/v1/generation/{engine}/text-to-image",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "text_prompts": [{"text": prompt}],
                    "cfg_scale": kwargs.get("cfg_scale", 7),
                    "width": int(w),
                    "height": int(h),
                    "samples": n,
                    "steps": kwargs.get("steps", 30),
                },
            )
            response.raise_for_status()
            data = response.json()

            for artifact in data.get("artifacts", []):
                img_data = base64.b64decode(artifact["base64"])
                images.append(img_data)

        return images


class ComfyUIImageBackend(ImageBackend):
    """Backend via ComfyUI (Stable Diffusion local) — 100% gratuito.

    Requer ComfyUI rodando localmente (http://localhost:8188).
    """

    async def generate(
        self, prompt: str, size: str = "1024x1024", n: int = 1, **kwargs: Any
    ) -> list[bytes]:
        import httpx
        import json
        import asyncio

        base_url = self.config.get("base_url") or os.getenv(
            "COMFYUI_BASE_URL", "http://localhost:8188"
        )
        w, h = size.split("x")

        # Workflow simplificado para geração de imagem
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": kwargs.get("seed", 42),
                    "steps": kwargs.get("steps", 20),
                    "cfg": kwargs.get("cfg_scale", 7.0),
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": self.config.get("model", "sd_xl_base_1.0.safetensors"),
                },
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": int(w), "height": int(h), "batch_size": n},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": kwargs.get("negative_prompt", "ugly, blurry, low quality"),
                    "clip": ["4", 1],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"images": ["8", 0], "filename_prefix": "omniachain"},
            },
        }

        images: list[bytes] = []
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Enviar prompt
            response = await client.post(
                f"{base_url}/prompt",
                json={"prompt": workflow},
            )
            response.raise_for_status()
            prompt_id = response.json().get("prompt_id")

            # Aguardar conclusão (polling)
            for _ in range(120):  # max 2 min
                await asyncio.sleep(1)
                history = await client.get(f"{base_url}/history/{prompt_id}")
                if history.status_code == 200:
                    hist_data = history.json()
                    if prompt_id in hist_data:
                        outputs = hist_data[prompt_id].get("outputs", {})
                        for node_id, output in outputs.items():
                            for img_info in output.get("images", []):
                                img_response = await client.get(
                                    f"{base_url}/view",
                                    params={
                                        "filename": img_info["filename"],
                                        "subfolder": img_info.get("subfolder", ""),
                                        "type": img_info.get("type", "output"),
                                    },
                                )
                                if img_response.status_code == 200:
                                    images.append(img_response.content)
                        break

        if not images:
            raise OmniaError(
                "ComfyUI não retornou imagens.",
                suggestion=f"Verifique se ComfyUI está rodando em {base_url}.",
            )

        return images


# ──────────────────────────────────────────────
# Classe principal
# ──────────────────────────────────────────────

class ImageGenerator:
    """Gerador de imagens com backends plugáveis.

    Exemplo::

        # DALL-E 3
        gen = ImageGenerator(backend="openai")
        await gen.generate_to_file("Um gato astronauta", "gato.png")

        # Google Nano Banana
        gen = ImageGenerator(backend="google")
        await gen.generate_to_file("Paisagem cyberpunk", "cidade.png")

        # Stable Diffusion local (ComfyUI)
        gen = ImageGenerator(backend="comfyui")
        await gen.generate_to_file("Retrato anime", "anime.png")

        # Qualquer API customizada
        ImageGenerator.register_backend("midjourney", MidjourneyBackend)
        gen = ImageGenerator(backend="midjourney")
    """

    _registry: dict[str, type[ImageBackend]] = {
        "openai": OpenAIImageBackend,
        "google": GoogleImageBackend,
        "nano-banana": GoogleImageBackend,  # Alias
        "stability": StabilityImageBackend,
        "comfyui": ComfyUIImageBackend,
    }

    def __init__(
        self,
        backend: str = "auto",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.backend_name = backend
        self._config = {
            "model": model, "api_key": api_key, "base_url": base_url, **kwargs
        }

        if backend == "auto":
            self._backend = self._auto_detect()
        else:
            if backend not in self._registry:
                raise OmniaError(
                    f"Backend de imagem '{backend}' não encontrado.",
                    suggestion=f"Backends disponíveis: {', '.join(self._registry.keys())}. "
                    f"Ou registre um novo com ImageGenerator.register_backend()",
                )
            self._backend = self._registry[backend](**self._config)

    def _auto_detect(self) -> ImageBackend:
        """Detecta o melhor backend disponível."""
        # 1. ComfyUI local
        try:
            import httpx
            # Tenta verificar se ComfyUI está rodando (sem bloquear)
            base_url = self._config.get("base_url") or os.getenv(
                "COMFYUI_BASE_URL", "http://localhost:8188"
            )
            self.backend_name = "comfyui"
            return ComfyUIImageBackend(**self._config)
        except Exception:
            pass

        # 2. OpenAI
        if os.getenv("OPENAI_API_KEY") or self._config.get("api_key"):
            self.backend_name = "openai"
            return OpenAIImageBackend(**self._config)

        # 3. Google
        if os.getenv("GOOGLE_API_KEY"):
            self.backend_name = "google"
            return GoogleImageBackend(**self._config)

        # 4. Stability
        if os.getenv("STABILITY_API_KEY"):
            self.backend_name = "stability"
            return StabilityImageBackend(**self._config)

        raise OmniaError(
            "Nenhum backend de geração de imagens disponível.",
            suggestion="Defina uma API key: OPENAI_API_KEY, GOOGLE_API_KEY, "
            "STABILITY_API_KEY, ou inicie ComfyUI localmente.",
        )

    @classmethod
    def register_backend(cls, name: str, backend_class: type[ImageBackend]) -> None:
        """Registra um backend customizado de geração de imagens.

        Exemplo::

            class FluxBackend(ImageBackend):
                async def generate(self, prompt, size="1024x1024", n=1, **kw):
                    # chamar API do Flux
                    return [image_bytes]

            ImageGenerator.register_backend("flux", FluxBackend)
        """
        cls._registry[name] = backend_class

    @classmethod
    def list_backends(cls) -> list[str]:
        """Lista todos os backends registrados."""
        return list(cls._registry.keys())

    async def generate(self, prompt: str, **kwargs: Any) -> list[bytes]:
        """Gera imagem(ns) a partir de prompt.

        Args:
            prompt: Descrição da imagem.
            **kwargs: size, n, e outros parâmetros do backend.

        Returns:
            Lista de bytes de imagens.
        """
        return await self._backend.generate(prompt, **kwargs)

    async def generate_to_file(
        self, prompt: str, output_path: Union[str, Path], **kwargs: Any
    ) -> Path:
        """Gera e salva a primeira imagem em arquivo.

        Args:
            prompt: Descrição da imagem.
            output_path: Caminho do arquivo de saída.

        Returns:
            Path do arquivo criado.
        """
        import aiofiles

        images = await self.generate(prompt, **kwargs)
        if not images:
            raise OmniaError(
                "Nenhuma imagem foi gerada.",
                suggestion="Tente novamente com um prompt diferente.",
            )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(path, "wb") as f:
            await f.write(images[0])

        return path

    async def generate_multiple(
        self, prompt: str, output_dir: Union[str, Path], n: int = 4, **kwargs: Any
    ) -> list[Path]:
        """Gera múltiplas imagens e salva em um diretório.

        Args:
            prompt: Descrição da imagem.
            output_dir: Diretório de saída.
            n: Número de imagens.

        Returns:
            Lista de Paths dos arquivos criados.
        """
        import aiofiles

        images = await self.generate(prompt, n=n, **kwargs)
        dir_path = Path(output_dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        paths: list[Path] = []
        for i, img_data in enumerate(images):
            file_path = dir_path / f"image_{i + 1}.png"
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(img_data)
            paths.append(file_path)

        return paths

    async def edit(self, image: bytes, prompt: str, **kwargs: Any) -> bytes:
        """Edita uma imagem existente com base em um prompt.

        Args:
            image: Bytes da imagem original.
            prompt: Instrução de edição.

        Returns:
            Bytes da imagem editada.
        """
        return await self._backend.edit(image, prompt, **kwargs)

    async def edit_file(
        self,
        image_path: Union[str, Path],
        prompt: str,
        output_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> Path:
        """Edita uma imagem de arquivo e salva o resultado.

        Args:
            image_path: Caminho da imagem original.
            prompt: Instrução de edição.
            output_path: Caminho de saída (padrão: sobrescreve original).

        Returns:
            Path do arquivo editado.
        """
        import aiofiles

        src = Path(image_path)
        async with aiofiles.open(src, "rb") as f:
            image_data = await f.read()

        edited = await self.edit(image_data, prompt, **kwargs)

        out = Path(output_path) if output_path else src
        async with aiofiles.open(out, "wb") as f:
            await f.write(edited)

        return out

    def __repr__(self) -> str:
        return f"ImageGenerator(backend={self.backend_name!r})"
