"""
OmniaChain — MCP Transport: stdio + HTTP/SSE.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, AsyncGenerator, Callable, Optional


class StdioTransport:
    """Transporte MCP via stdin/stdout (JSON-RPC)."""

    def __init__(self, handler: Callable) -> None:
        self.handler = handler

    async def run(self) -> None:
        """Loop principal de leitura stdin e escrita stdout."""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout.buffer
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())

        while True:
            try:
                # Ler header Content-Length
                header = await reader.readline()
                if not header:
                    break

                header_str = header.decode().strip()
                if header_str.startswith("Content-Length:"):
                    length = int(header_str.split(":")[1].strip())
                    await reader.readline()  # Empty line
                    data = await reader.readexactly(length)
                    request = json.loads(data)

                    response = await self.handler(request)
                    if response:
                        response_data = json.dumps(response).encode()
                        writer.write(f"Content-Length: {len(response_data)}\r\n\r\n".encode())
                        writer.write(response_data)
                        await writer.drain()

            except (asyncio.IncompleteReadError, ConnectionError):
                break
            except Exception:
                continue


class HTTPTransport:
    """Transporte MCP via HTTP com SSE para notificações."""

    def __init__(self, handler: Callable, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.handler = handler
        self.host = host
        self.port = port

    async def run(self) -> None:
        """Inicia servidor HTTP para MCP."""
        import httpx

        server = await asyncio.start_server(
            self._handle_connection, self.host, self.port
        )

        async with server:
            await server.serve_forever()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Processa uma conexão HTTP."""
        try:
            request_data = await reader.read(65536)
            if not request_data:
                return

            # Parse HTTP request simplistamente
            request_str = request_data.decode()
            lines = request_str.split("\r\n")

            # Encontrar body
            body = ""
            body_start = request_str.find("\r\n\r\n")
            if body_start >= 0:
                body = request_str[body_start + 4:]

            if body:
                try:
                    request = json.loads(body)
                    response = await self.handler(request)

                    response_body = json.dumps(response).encode()
                    http_response = (
                        f"HTTP/1.1 200 OK\r\n"
                        f"Content-Type: application/json\r\n"
                        f"Content-Length: {len(response_body)}\r\n"
                        f"Access-Control-Allow-Origin: *\r\n"
                        f"\r\n"
                    ).encode() + response_body

                    writer.write(http_response)
                    await writer.drain()
                except json.JSONDecodeError:
                    pass

        except Exception:
            pass
        finally:
            writer.close()
