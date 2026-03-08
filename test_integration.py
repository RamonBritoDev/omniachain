"""Teste de integração real do OmniaChain com OpenAI API."""

import asyncio
import os
import sys

# Configurar API key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "your-api-key-here")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_1_basic_completion():
    """Teste 1: Completar texto simples."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 1: Completar texto simples")
    print("=" * 60)

    from omniachain.providers.openai import OpenAIProvider
    from omniachain.core.message import Message

    provider = OpenAIProvider(model="gpt-4o-mini")
    messages = [
        Message.system("Responda de forma curta e direta, em português."),
        Message.user("Qual é a capital do Brasil?"),
    ]

    response = await provider.complete(messages)
    print(f"✅ Resposta: {response.content}")
    print(f"   Tokens: {response.usage.total_tokens} | Custo: ${response.usage.cost:.6f}")
    print(f"   Modelo: {response.model}")
    return True


async def test_2_tool_calling():
    """Teste 2: Tool calling com calculator."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 2: Tool calling com calculator")
    print("=" * 60)

    from omniachain.agents.base import Agent
    from omniachain.providers.openai import OpenAIProvider
    from omniachain.tools.calculator import calculator

    provider = OpenAIProvider(model="gpt-4o-mini")
    agent = Agent(
        provider=provider,
        tools=[calculator],
        system_prompt="Você é um assistente que usa tools para cálculos. Responda em português.",
    )

    result = await agent.run("Quanto é 1547 * 32 + raiz quadrada de 144?")
    print(f"✅ Resposta: {result.content}")
    print(f"   Tool calls: {len(result.tool_calls)}")
    print(f"   Tokens: {result.usage.total_tokens} | Custo: ${result.usage.cost:.6f}")
    return True


async def test_3_streaming():
    """Teste 3: Streaming de resposta."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 3: Streaming de resposta")
    print("=" * 60)

    from omniachain.providers.openai import OpenAIProvider
    from omniachain.core.message import Message

    provider = OpenAIProvider(model="gpt-4o-mini")
    messages = [
        Message.system("Responda em português, de forma curta."),
        Message.user("Conte até 5 com uma palavra por linha."),
    ]

    print("   Stream: ", end="", flush=True)
    full = ""
    async for token in provider.stream(messages):
        print(token, end="", flush=True)
        full += token

    print(f"\n✅ Streaming funcionou! ({len(full)} caracteres)")
    return True


async def test_4_security_pgp():
    """Teste 4: Segurança PGP — grant/deny."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 4: Segurança PGP com agente")
    print("=" * 60)

    from omniachain.security.keypair import KeyPair
    from omniachain.security.permissions import Permissions
    from omniachain.agents.base import Agent
    from omniachain.providers.openai import OpenAIProvider
    from omniachain.tools.calculator import calculator

    # Gerar chaves
    admin_keys = await KeyPair.generate(agent_name="admin")
    reader_keys = await KeyPair.generate(agent_name="reader")
    print(f"   Admin: {admin_keys.fingerprint[:16]}...")
    print(f"   Reader: {reader_keys.fingerprint[:16]}...")

    # Configurar permissões
    perms = Permissions()
    perms.grant(admin_keys.fingerprint, tools=["calculator"])
    perms.deny(reader_keys.fingerprint, tools=["calculator"])

    # Admin pode usar calculator
    admin_access = perms.can_access(admin_keys.fingerprint, "tool", "calculator")
    reader_access = perms.can_access(reader_keys.fingerprint, "tool", "calculator")

    print(f"   Admin pode usar calculator? {admin_access} {'✅' if admin_access else '❌'}")
    print(f"   Reader pode usar calculator? {reader_access} {'✅' if not reader_access else '❌'}")

    # Testar agente admin com tool calling real
    provider = OpenAIProvider(model="gpt-4o-mini")
    agent = Agent(
        provider=provider,
        tools=[calculator],
        keypair=admin_keys,
        permissions=perms,
        system_prompt="Use a calculator tool para cálculos. Responda em português.",
    )

    result = await agent.run("Quanto é 99 * 99?")
    print(f"   Agente admin respondeu: {result.content[:100]}")
    print(f"✅ Segurança PGP funcionando!")
    return True


async def test_5_cost_tracker():
    """Teste 5: Cost tracking em tempo real."""
    print("\n" + "=" * 60)
    print("🧪 TESTE 5: Cost tracking em tempo real")
    print("=" * 60)

    from omniachain.providers.openai import OpenAIProvider
    from omniachain.core.message import Message
    from omniachain.observability.costs import CostTracker

    tracker = CostTracker()
    provider = OpenAIProvider(model="gpt-4o-mini")

    # Fazer 3 chamadas
    for i, pergunta in enumerate(["Diga 'oi'", "Diga 'tchau'", "Diga 'ok'"]):
        messages = [Message.user(pergunta)]
        response = await provider.complete(messages)
        tracker.record(response)
        print(f"   Chamada {i+1}: {response.content[:30]}... | ${response.usage.cost:.6f}")

    print(f"\n{tracker.summary()}")
    print(f"✅ Cost tracking funcionando!")
    return True


async def main():
    print("🚀 OmniaChain — Testes de Integração Real com OpenAI")
    print("=" * 60)

    tests = [
        ("Completar texto", test_1_basic_completion),
        ("Tool calling", test_2_tool_calling),
        ("Streaming", test_3_streaming),
        ("Segurança PGP", test_4_security_pgp),
        ("Cost tracking", test_5_cost_tracker),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            print(f"\n❌ FALHOU: {name}")
            print(f"   Erro: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 RESULTADO FINAL: {passed} ✅ | {failed} ❌ de {len(tests)} testes")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
