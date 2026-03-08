"""OmniaChain — Tool de requisições HTTP com retry automático."""

from omniachain.tools.base import tool


@tool(retries=3, timeout=30.0)
async def http_request(
    url: str,
    method: str = "GET",
    headers: str = "{}",
    body: str = "",
) -> str:
    """Faz requisições HTTP com retry automático.

    Args:
        url: URL do endpoint.
        method: Método HTTP (GET, POST, PUT, DELETE, PATCH).
        headers: Headers em formato JSON string.
        body: Corpo da requisição (para POST/PUT/PATCH).

    Returns:
        Resposta com status code e corpo.
    """
    import json
    import httpx

    parsed_headers = json.loads(headers) if headers and headers != "{}" else {}

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        kwargs: dict = {"headers": parsed_headers}
        if method.upper() in ("POST", "PUT", "PATCH") and body:
            kwargs["content"] = body

        response = await client.request(method.upper(), url, **kwargs)

        result_parts = [
            f"Status: {response.status_code}",
            f"Content-Type: {response.headers.get('content-type', 'unknown')}",
        ]

        # Tentar JSON primeiro
        try:
            data = response.json()
            result_parts.append(f"Body (JSON):\n{json.dumps(data, indent=2, ensure_ascii=False)[:5000]}")
        except Exception:
            text = response.text[:5000]
            result_parts.append(f"Body:\n{text}")

        return "\n".join(result_parts)
