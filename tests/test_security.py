"""Testes — Security: keypair, permissions, middleware."""

import pytest
import asyncio
from omniachain.security.keypair import KeyPair
from omniachain.security.permissions import Permissions, AccessLevel
from omniachain.security.middleware import SecurityMiddleware
from omniachain.core.errors import SecurityError


class TestKeyPair:
    @pytest.mark.asyncio
    async def test_generate_hmac(self):
        keys = await KeyPair.generate(agent_name="test-agent")
        assert keys.agent_name == "test-agent"
        assert len(keys.fingerprint) == 40
        assert keys.public_key
        assert keys.private_key

    @pytest.mark.asyncio
    async def test_sign_verify(self):
        keys = await KeyPair.generate(agent_name="signer")
        data = b"dados importantes"
        signature = await keys.sign(data)
        assert await keys.verify(data, signature)

    @pytest.mark.asyncio
    async def test_invalid_signature(self):
        keys = await KeyPair.generate(agent_name="signer")
        data = b"dados"
        assert not await keys.verify(data, "assinatura-invalida")


class TestPermissions:
    def test_grant_and_check(self):
        perms = Permissions()
        perms.grant("fp-001", tools=["web_search", "calculator"])
        assert perms.can_access("fp-001", "tool", "web_search")
        assert perms.can_access("fp-001", "tool", "calculator")
        assert not perms.can_access("fp-001", "tool", "code_exec")

    def test_deny(self):
        perms = Permissions()
        perms.grant("fp-001", tools=["web_search"])
        perms.deny("fp-001", tools=["web_search"])
        assert not perms.can_access("fp-001", "tool", "web_search")

    def test_all_resources(self):
        perms = Permissions()
        perms.grant("fp-admin", all_resources=True)
        assert perms.can_access("fp-admin", "tool", "anything")
        assert perms.can_access("fp-admin", "memory", "read")

    def test_unknown_agent(self):
        perms = Permissions()
        assert not perms.can_access("unknown", "tool", "anything")

    def test_allowed_resources(self):
        perms = Permissions()
        perms.grant("fp-001", tools=["a", "b", "c"])
        perms.deny("fp-001", tools=["b"])
        allowed = perms.get_allowed_resources("fp-001", "tool")
        assert "a" in allowed
        assert "c" in allowed
        assert "b" not in allowed


class TestMiddleware:
    @pytest.mark.asyncio
    async def test_validate_success(self):
        keys = await KeyPair.generate(agent_name="admin")
        perms = Permissions()
        perms.grant(keys.fingerprint, tools=["web_search"])

        middleware = SecurityMiddleware(permissions=perms)
        req = await middleware.validate_request(keys, "tool", "web_search")
        assert req.agent_name == "admin"

    @pytest.mark.asyncio
    async def test_validate_denied(self):
        keys = await KeyPair.generate(agent_name="reader")
        perms = Permissions()
        # No grant

        middleware = SecurityMiddleware(permissions=perms)
        with pytest.raises(SecurityError):
            await middleware.validate_request(keys, "tool", "web_search")

    @pytest.mark.asyncio
    async def test_audit_log(self):
        keys = await KeyPair.generate(agent_name="tester")
        perms = Permissions()
        perms.grant(keys.fingerprint, tools=["calc"])
        middleware = SecurityMiddleware(permissions=perms)
        await middleware.validate_request(keys, "tool", "calc")
        log = middleware.get_audit_log()
        assert len(log) >= 1
        assert log[-1]["decision"] == "ALLOWED"
