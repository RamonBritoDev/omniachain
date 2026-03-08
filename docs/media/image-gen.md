# Geração de Imagens

Gere imagens com qualquer API — DALL-E, Google Nano Banana, Stability AI, Stable Diffusion local, ou qualquer backend customizado.

## Backends

| Backend | Tipo | Requer | Modelos |
|---------|------|--------|---------|
| `openai` | API | `OPENAI_API_KEY` | DALL-E 3, DALL-E 2 |
| `google` / `nano-banana` | API | `GOOGLE_API_KEY` | Gemini Image (Nano Banana) |
| `stability` | API | `STABILITY_API_KEY` | SDXL, SD3 |
| `comfyui` | Local | ComfyUI rodando | Qualquer modelo .safetensors |
| `auto` | — | Detecta automaticamente | — |

## Uso Básico

```python
from omniachain import ImageGenerator

# DALL-E 3
gen = ImageGenerator(backend="openai")
await gen.generate_to_file("Um gato astronauta no espaço", "gato.png")

# Google Nano Banana
gen = ImageGenerator(backend="nano-banana")
await gen.generate_to_file("Paisagem cyberpunk", "cidade.png")

# Stability AI
gen = ImageGenerator(backend="stability")
await gen.generate_to_file("Logo minimalista", "logo.png")

# ComfyUI (Stable Diffusion local — grátis)
gen = ImageGenerator(backend="comfyui")
await gen.generate_to_file("Retrato estilo anime", "anime.png")
```

## Múltiplas Imagens

```python
gen = ImageGenerator(backend="openai")

# Gerar uma lista de bytes
images = await gen.generate("Um gato programador", n=3)

# Ou salvar direto em diretório
paths = await gen.generate_multiple(
    "Variações de um logo",
    output_dir="./logos",
    n=4,
)
```

## Editar Imagens

```python
gen = ImageGenerator(backend="openai")

# Editar a partir de bytes
with open("foto.png", "rb") as f:
    editada = await gen.edit(f.read(), "Adicione um chapéu de cowboy")

# Editar arquivo direto
await gen.edit_file("foto.png", "Mude o fundo para praia", output_path="foto_praia.png")
```

!!! note
    Edição disponível em backends `openai` e `google`. Outros backends podem não suportar.

## Tamanhos Suportados

| Backend | Tamanhos |
|---------|----------|
| DALL-E 3 | `1024x1024`, `1792x1024`, `1024x1792` |
| Nano Banana | Flexível |
| Stability | `1024x1024`, `512x512`, `768x768` |
| ComfyUI | Qualquer resolução |

## ArtistAgent

Agente que otimiza prompts automaticamente antes de gerar:

```python
from omniachain import ArtistAgent, OpenAI

artist = ArtistAgent(provider=OpenAI(), image_backend="openai")

# O LLM otimiza o prompt antes de gerar
await artist.create("Logo para minha cafeteria", "logo.png")

# Múltiplas variações
await artist.create_variations("Photo-realistic cat with glasses", "gatos/", n=4)

# Editar
await artist.edit_image("foto.png", "Torne mais vibrante", "foto_v2.png")
```

## Backend Customizado

Conecte **qualquer API** de geração de imagens:

```python
from omniachain.media.image_gen import ImageBackend, ImageGenerator

class ReplicateBackend(ImageBackend):
    async def generate(self, prompt, size="1024x1024", n=1, **kw):
        import replicate
        output = replicate.run("stability-ai/sdxl", input={"prompt": prompt})
        # Baixar a imagem
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(output[0])
            return [resp.content]

ImageGenerator.register_backend("replicate", ReplicateBackend)
gen = ImageGenerator(backend="replicate")
await gen.generate_to_file("Ocean sunset", "sunset.png")
```

### Exemplos de backends que você pode criar:

- **Midjourney** (via Discord API ou proxy)
- **Leonardo AI**
- **Flux** (via Replicate ou local)
- **Ideogram**
- **Fooocus** (interface Gradio local)

## Parâmetros

| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `backend` | `str` | `"auto"` | Backend a usar |
| `model` | `str` | `None` | Modelo específico |
| `api_key` | `str` | `None` | API key |
| `base_url` | `str` | `None` | URL base (para ComfyUI, etc.) |

!!! warning "API Keys"
    Configure via variáveis de ambiente:
    ```bash
    export OPENAI_API_KEY="sk-..."
    export GOOGLE_API_KEY="AIza..."
    export STABILITY_API_KEY="sk-..."
    ```
