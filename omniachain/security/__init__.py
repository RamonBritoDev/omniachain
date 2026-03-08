"""OmniaChain security — autenticação e autorização PGP para agentes."""

from omniachain.security.keypair import KeyPair
from omniachain.security.permissions import Permissions, Permission
from omniachain.security.guard import requires_permission, SecurityGuard
from omniachain.security.middleware import SecurityMiddleware

__all__ = [
    "KeyPair", "Permissions", "Permission",
    "requires_permission", "SecurityGuard",
    "SecurityMiddleware",
]
