"""Exemplo 05 — Segurança PGP: controle de acesso a tools e memória."""

import asyncio
from omniachain import (
    Agent, Anthropic,
    KeyPair, Permissions, SecurityGuard,
    calculator, web_search,
)
from omniachain.security.guard import set_global_guard
from omniachain.security.middleware import SecurityMiddleware


async def main():
    # 1. Gerar chaves PGP para cada agente
    admin_keys = await KeyPair.generate(agent_name="admin")
    reader_keys = await KeyPair.generate(agent_name="reader")

    print(f"Admin fingerprint: {admin_keys.fingerprint[:16]}...")
    print(f"Reader fingerprint: {reader_keys.fingerprint[:16]}...")

    # 2. Configurar permissões
    perms = Permissions()
    perms.grant(admin_keys.fingerprint, all_resources=True)  # Admin acessa tudo
    perms.grant(reader_keys.fingerprint, tools=["calculator"])  # Reader só calcula
    perms.deny(reader_keys.fingerprint, tools=["web_search", "code_exec"])

    # 3. Verificar permissões
    print(f"\nAdmin pode usar web_search? {perms.can_access(admin_keys.fingerprint, 'tool', 'web_search')}")
    print(f"Reader pode usar calculator? {perms.can_access(reader_keys.fingerprint, 'tool', 'calculator')}")
    print(f"Reader pode usar web_search? {perms.can_access(reader_keys.fingerprint, 'tool', 'web_search')}")

    # 4. Middleware com assinatura PGP
    middleware = SecurityMiddleware(permissions=perms)

    # Validar requisição do admin (deve passar)
    try:
        req = await middleware.validate_request(
            keypair=admin_keys,
            resource_type="tool",
            resource_name="web_search",
        )
        print(f"\n✅ Admin aprovado para web_search")
    except Exception as e:
        print(f"\n❌ Admin negado: {e}")

    # Validar requisição do reader para web_search (deve falhar)
    try:
        req = await middleware.validate_request(
            keypair=reader_keys,
            resource_type="tool",
            resource_name="web_search",
        )
        print(f"✅ Reader aprovado para web_search")
    except Exception as e:
        print(f"❌ Reader negado: {e}")

    # 5. Log de auditoria
    print("\n📋 Log de auditoria:")
    for entry in middleware.get_audit_log():
        print(f"  [{entry['decision']}] {entry['agent']} → {entry['resource']}")

    # 6. Criar agente com segurança
    agent = Agent(
        provider=Anthropic(),
        tools=[calculator, web_search],
        keypair=admin_keys,
        permissions=perms,
    )
    # result = await agent.run("Quanto é 2 + 2?")


if __name__ == "__main__":
    asyncio.run(main())
