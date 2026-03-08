# Instalação

## Requisitos

- Python **3.11+**
- pip ou poetry

## Instalação Básica

```bash
pip install omniachain
```

## Instalação com Extras

=== "Todos os extras"

    ```bash
    pip install omniachain[all]
    ```

=== "Vetorial (pgvector)"

    ```bash
    pip install omniachain[vector]
    ```

=== "Browser (Playwright)"

    ```bash
    pip install omniachain[browser]
    playwright install chromium
    ```

=== "Áudio (Whisper)"

    ```bash
    pip install omniachain[audio]
    ```

## Desenvolvimento Local

```bash
git clone https://github.com/omniachain/omniachain.git
cd omniachain
pip install -e ".[all]"
pytest tests/ -v
```

## Dependências do Sistema

!!! info "FFmpeg (para vídeo e áudio)"
    O `VideoLoader` e `AudioLoader` precisam do ffmpeg:

    === "Windows"
        ```bash
        winget install Gyan.FFmpeg
        ```

    === "macOS"
        ```bash
        brew install ffmpeg
        ```

    === "Linux"
        ```bash
        sudo apt install ffmpeg
        ```

## Variáveis de Ambiente

Crie um `.env` ou exporte:

```bash
# API Keys (pelo menos um)
export ANTHROPIC_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."
export GOOGLE_API_KEY="..."

# Configuração opcional
export OMNIA_DEFAULT_PROVIDER="anthropic"
export OMNIA_DEFAULT_MODEL="claude-3-5-sonnet-20241022"
export OMNIA_PGVECTOR_DSN="postgresql://user:pass@localhost/omniachain"
export OMNIA_SECURITY_ENABLED="true"
```

!!! success "Pronto!"
    Agora siga para [Primeiro Agente](first-agent.md) →
