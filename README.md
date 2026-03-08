<div align="center">
  <img src="https://raw.githubusercontent.com/RamonBritoDev/omniachain/main/docs-site/public/favicon.ico" alt="OmniaChain" width="120" />
  <h1>✨ OmniaChain</h1>
  
  <p><b>Python framework for AI agents — async-first, multi-modal, native MCP.</b></p>

  <p>
    <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11+-8b5cf6?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-a78bfa?style=for-the-badge" alt="License: MIT" /></a>
    <a href="https://github.com/RamonBritoDev/omniachain"><img src="https://img.shields.io/badge/Version-1.0.0-c4b5fd?style=for-the-badge" alt="Version 1.0.0" /></a>
  </p>

  <i>Intelligent orchestration, native integration, and built-in security for your agents.</i><br/><br/>
</div>

<hr/>

## 🔮 Why OmniaChain?

Everything you need to build next-generation artificial intelligence in one place. OmniaChain was designed focusing on **speed, extensibility, and modularity** for truly capable agents.

### ✨ Key Features

- ⚡ **Automatic Async-first**: Asynchronous parallel pipeline (`asyncio`) to ensure maximum performance when executing tools and LLM calls. Zero blocking.
- 🎨 **Multimodal Agents**: Computer vision, audio inputs (STT), video transcription, and synthetic voice generation (TTS) + image generation. Everything is embedded and processed dynamically: _Text, PDF, image, audio, video, CSV, URL, code_.
- 🫂 **Model Context Protocol (MCP)**: **Native** integration with Anthropic's MCP servers, allowing you to instantly inject dozens of standardized tools via `stdio` or `http`.
- 🧠 **Multiple Providers**: Work with `Anthropic`, `OpenAI`, `Groq`, `Ollama`, and `Google Gemini` simultaneously, or apply advanced *Fallback* rules.
- 🛡️ **Military-grade PGP Security**: Keypairs, contextual permissions, guard middlewares with GPG signature support and auditing for restricted tools (`code_exec`, etc).
- 🧩 **Modular Multi-Agent**: Configure complex architectures with ReAct, Multimodal, Planner, and Supervisor agents integrated with advanced vector memory (pgvector).

---

## 🚀 Quick Installation

OmniaChain is modular. Install only what you need or embark on the full ship.

```bash
# Basic framework installation
pip install omniachain

# Complete Installation (Recommended)
pip install omniachain[all]

# Specific extras to enable powerful dependencies
pip install omniachain[vector]    # Advanced Memory with PostgreSQL pgvector
pip install omniachain[browser]   # Automation and web scraping with Playwright
pip install omniachain[audio]     # Local transcription (STT) using the Whisper engine
```

---

## ⚡ Quick Start (3 Lines!)

**You don't need huge boilerplates. Summon an agent with tools in 3 lines of code:**

```python
import asyncio
from omniachain import Agent, OpenAI, calculator, web_search

async def main():
    agent = Agent(provider=OpenAI("gpt-4o-mini"), tools=[calculator, web_search])
    
    # The agent decides entirely on its own when to invoke web tools or calculations!
    result = await agent.run("What is the square root of 144 times the distance to the moon?")
    
    print(result.content)

asyncio.run(main())
```

<hr/>

### 👁️ Advanced Multi-modal Agent
Connect raw and mixed data sources directly to prompts:

```python
from omniachain import MultimodalAgent, Anthropic

agent = MultimodalAgent(provider=Anthropic("claude-3-5-sonnet-20241022"))
result = await agent.run(
    "Extract key metrics, transcribe the recording, and compare against the visual projection.",
    inputs=["sales_report.pdf", "audio_meeting.mp3", "q4_projection.png"]
)
```

<hr/>

### 🔌 MCP Server (Direct Integration)
Instantly transform OmniaChain tools into a Model Context Protocol server accessible via Claude Desktop:

```python
from omniachain import MCPServer

server = MCPServer("hr-database")

@server.tool
async def check_vacation(role: str) -> str:
    """Checks vacation rules based on role."""
    return f"Policies and deadlines for the role: {role}"

# Start MCP communication transport
await server.run(transport="stdio")
```

<hr/>

### 🛡️ PGP Security & Permissions
Lock down dangerous executions by binding LLM execution to OmniaChain cryptographic PGP signatures:

```python
from omniachain import Agent, KeyPair, Permissions

keys = await KeyPair.generate(agent_name="sysadmin")
perms = Permissions()

# Only this fingerprint is authorized to use the calculator
perms.grant(keys.fingerprint, tools=["calculator"])  
# The agent will never run remote executions, even if it suffers a prompt injection
perms.deny(keys.fingerprint, tools=["code_exec"])    

agent = Agent(provider=..., tools=[...], keypair=keys, permissions=perms)
```

---

## 🏗️ Framework Architecture

OmniaChain was written to be easy to contribute to and insanely powerful to use:

```text
omniachain/
├── core/           # Universal Configs, Messages, Responses, and Errors
├── providers/      # Endpoints: Anthropic, OpenAI, Groq, Ollama, Google
├── loaders/        # Auto-ingestion: PDF, Image, Audio, Video, CSV, URL, Code
├── tools/          # Web Search, Browser, Calculator, HTTP Exec and @tool decorator
├── memory/         # Buffer, Summary, Vector Context (pgvector), Persistent, MCP
├── mcp/            # MCP Client and Server, HTTP Protocol and STDIO Transport
├── security/       # PGP Signatures, Permission Guard, Middleware Auditing
├── agents/         # Workflow Base: ReAct, Multimodal, Planner, Supervisor, Voice
├── pipeline/       # Graphs: Sequential, Parallel, Conditional, Router
├── orchestration/  # Session Management, Multi-Agent and Cost Pooling
└── observability/  # Dynamic Logging, Active Tracing, and Dashboard
```

---

## 📁 Essential Environment Variables

Create a `.env` file at the root or export them in the terminal. The framework will magically instantiate the keys.

| Variable | Configuration |
|----------|-----------|
| `ANTHROPIC_API_KEY` | Anthropic LLM Authentication |
| `OPENAI_API_KEY` | OpenAI LLM Authentication |
| `GROQ_API_KEY` | Fast Groq LPU Endpoint |
| `GOOGLE_API_KEY` | Google Gemini Authentication |
| `OMNIA_DEFAULT_PROVIDER` | Default fallback provider in the system |
| `OMNIA_PGVECTOR_DSN` | Connection with the PostgreSQL vector database |
| `OMNIA_SECURITY_ENABLED` | *Boolean* to enable strict PGP request signing |

---

<div align="center">
  <p><b>Made with 💜 for the global Artificial Intelligence community.</b></p>
  <a href="LICENSE">Distributed under the MIT License. Commercial Use, Modification, and Distribution permitted.</a>
</div>
