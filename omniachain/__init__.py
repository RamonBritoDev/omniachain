"""
OmniaChain — Framework Python para agentes de IA.

Async-first, multi-modal, MCP nativo, orquestração multi-agente.

Exemplo::

    from omniachain import Agent, Anthropic, web_search, calculator

    agent = Agent(
        provider=Anthropic(),
        tools=[web_search, calculator],
    )
    result = await agent.run("Qual o PIB do Brasil?")
    print(result.content)
"""

__version__ = "0.1.0"

# Core
from omniachain.core.errors import OmniaError, ProviderError, ToolError, SecurityError
from omniachain.core.config import OmniaConfig, get_config
from omniachain.core.message import Message, MessageContent
from omniachain.core.response import Response, Usage
from omniachain.core.context import Context
from omniachain.core.chain import Chain, Step

# Providers
from omniachain.providers.anthropic import AnthropicProvider as Anthropic
from omniachain.providers.openai import OpenAIProvider as OpenAI
from omniachain.providers.groq import GroqProvider as Groq
from omniachain.providers.ollama import OllamaProvider as Ollama
from omniachain.providers.google import GoogleProvider as Google

# Agents
from omniachain.agents.base import Agent
from omniachain.agents.react import ReActAgent
from omniachain.agents.multimodal import MultimodalAgent
from omniachain.agents.planner import PlannerAgent
from omniachain.agents.supervisor import SupervisorAgent
from omniachain.agents.voice import VoiceAgent
from omniachain.agents.artist import ArtistAgent

# Tools
from omniachain.tools.base import tool, Tool
from omniachain.tools.calculator import calculator
from omniachain.tools.web_search import web_search
from omniachain.tools.http import http_request
from omniachain.tools.file import file_read, file_write
from omniachain.tools.code_exec import code_exec
from omniachain.tools.stt_tool import speech_to_text
from omniachain.tools.tts_tool import text_to_speech
from omniachain.tools.image_gen_tool import generate_image

# Memory
from omniachain.memory.buffer import BufferMemory
from omniachain.memory.summary import SummaryMemory
from omniachain.memory.vector import VectorMemory
from omniachain.memory.persistent import PersistentMemory

# MCP
from omniachain.mcp.server import MCPServer
from omniachain.mcp.client import MCPClient

# Pipeline
from omniachain.pipeline.sequential import SequentialPipeline
from omniachain.pipeline.parallel import ParallelPipeline

# Orchestration
from omniachain.orchestration.session import Session
from omniachain.orchestration.pool import ProviderPool

# Security
from omniachain.security.keypair import KeyPair
from omniachain.security.permissions import Permissions
from omniachain.security.guard import SecurityGuard

# Observability
from omniachain.observability.logger import get_logger
from omniachain.observability.tracer import Tracer
from omniachain.observability.costs import CostTracker

# Loaders
from omniachain.loaders.auto import AutoLoader

# Media — STT, TTS, Geração de Imagens
from omniachain.media.stt import SpeechToText, STTBackend
from omniachain.media.tts import TextToSpeech, TTSBackend
from omniachain.media.image_gen import ImageGenerator, ImageBackend

__all__ = [
    # Core
    "OmniaError", "ProviderError", "ToolError", "SecurityError",
    "OmniaConfig", "get_config",
    "Message", "MessageContent", "Response", "Usage",
    "Context", "Chain", "Step",
    # Providers
    "Anthropic", "OpenAI", "Groq", "Ollama", "Google",
    # Agents
    "Agent", "ReActAgent", "MultimodalAgent", "PlannerAgent", "SupervisorAgent",
    "VoiceAgent", "ArtistAgent",
    # Tools
    "tool", "Tool", "calculator", "web_search", "http_request",
    "file_read", "file_write", "code_exec",
    "speech_to_text", "text_to_speech", "generate_image",
    # Memory
    "BufferMemory", "SummaryMemory", "VectorMemory", "PersistentMemory",
    # MCP
    "MCPServer", "MCPClient",
    # Pipeline
    "SequentialPipeline", "ParallelPipeline",
    # Orchestration
    "Session", "ProviderPool",
    # Security
    "KeyPair", "Permissions", "SecurityGuard",
    # Observability
    "get_logger", "Tracer", "CostTracker",
    # Loaders
    "AutoLoader",
    # Media
    "SpeechToText", "STTBackend",
    "TextToSpeech", "TTSBackend",
    "ImageGenerator", "ImageBackend",
]

