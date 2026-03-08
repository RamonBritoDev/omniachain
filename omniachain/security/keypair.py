"""
OmniaChain — Geração e gerenciamento de pares de chaves PGP.

Cada agente pode ter seu próprio par de chaves para assinar requisições.

Exemplo::

    keys = await KeyPair.generate(agent_name="researcher")
    signature = await keys.sign(b"dados para assinar")
    is_valid = await keys.verify(b"dados para assinar", signature)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import secrets
import tempfile
from typing import Optional

from pydantic import BaseModel, Field

from omniachain.core.errors import SecurityError


class KeyPair(BaseModel):
    """Par de chaves PGP para autenticação de agentes.

    Gerencia geração, assinatura e verificação de chaves.

    Exemplo::

        keys = await KeyPair.generate(agent_name="analyst")
        sig = await keys.sign(b"my data")
        assert await keys.verify(b"my data", sig)
    """

    agent_name: str
    fingerprint: str = ""
    public_key: str = ""
    private_key: str = ""  # Em produção, armazenar de forma segura
    _gpg_home: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    async def generate(
        cls,
        agent_name: str,
        gpg_home: Optional[str] = None,
        use_gpg: bool = False,
    ) -> KeyPair:
        """Gera um novo par de chaves para o agente.

        Args:
            agent_name: Nome do agente dono das chaves.
            gpg_home: Diretório do keyring GPG. None = tempdir.
            use_gpg: Se True, usa GPG real. Se False, usa HMAC simplificado.

        Returns:
            KeyPair com chaves geradas.
        """
        if use_gpg:
            return await cls._generate_gpg(agent_name, gpg_home)
        else:
            return await cls._generate_hmac(agent_name)

    @classmethod
    async def _generate_gpg(cls, agent_name: str, gpg_home: Optional[str] = None) -> KeyPair:
        """Gera chaves usando GPG real (python-gnupg)."""
        try:
            import gnupg
        except ImportError:
            raise SecurityError(
                "Pacote 'python-gnupg' não instalado.",
                agent_name=agent_name,
                resource="key_generation",
                suggestion="Instale com: pip install python-gnupg",
            )

        home = gpg_home or tempfile.mkdtemp(prefix="omniachain_gpg_")

        try:
            gpg = gnupg.GPG(gnupghome=home)

            input_data = gpg.gen_key_input(
                key_type="RSA",
                key_length=2048,
                name_real=agent_name,
                name_email=f"{agent_name}@omniachain.local",
                passphrase="",
            )

            key = await asyncio.to_thread(gpg.gen_key, input_data)

            if not key:
                raise SecurityError(
                    "Falha ao gerar chave GPG.",
                    agent_name=agent_name,
                    resource="key_generation",
                )

            fingerprint = str(key)
            public_key = await asyncio.to_thread(gpg.export_keys, fingerprint)
            private_key = await asyncio.to_thread(gpg.export_keys, fingerprint, True)

            instance = cls(
                agent_name=agent_name,
                fingerprint=fingerprint,
                public_key=str(public_key),
                private_key=str(private_key),
            )
            instance._gpg_home = home
            return instance

        except SecurityError:
            raise
        except Exception as e:
            raise SecurityError(
                f"Erro ao gerar chaves GPG: {e}",
                agent_name=agent_name,
                resource="key_generation",
                original_error=e,
            )

    @classmethod
    async def _generate_hmac(cls, agent_name: str) -> KeyPair:
        """Gera chaves simplificadas usando HMAC-SHA256 (sem GPG externo)."""
        secret = secrets.token_hex(32)
        public_id = hashlib.sha256(f"{agent_name}:{secret}".encode()).hexdigest()
        fingerprint = public_id[:40]

        return cls(
            agent_name=agent_name,
            fingerprint=fingerprint,
            public_key=public_id,
            private_key=secret,
        )

    async def sign(self, data: bytes) -> str:
        """Assina dados com a chave privada.

        Args:
            data: Dados para assinar.

        Returns:
            Assinatura em formato hex.
        """
        if not self.private_key:
            raise SecurityError(
                "Chave privada não disponível para assinatura.",
                agent_name=self.agent_name,
                resource="signing",
            )

        # Se temos GPG home, usar GPG real
        if self._gpg_home:
            return await self._sign_gpg(data)

        # HMAC simplificado
        signature = hmac.new(
            self.private_key.encode(),
            data,
            hashlib.sha256,
        ).hexdigest()
        return signature

    async def verify(self, data: bytes, signature: str) -> bool:
        """Verifica assinatura dos dados.

        Args:
            data: Dados originais.
            signature: Assinatura para verificar.

        Returns:
            True se a assinatura é válida.
        """
        if self._gpg_home:
            return await self._verify_gpg(data, signature)

        expected = hmac.new(
            self.private_key.encode(),
            data,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def _sign_gpg(self, data: bytes) -> str:
        """Assina dados com GPG real."""
        import gnupg

        gpg = gnupg.GPG(gnupghome=self._gpg_home)
        signed = await asyncio.to_thread(
            gpg.sign, data.decode("utf-8", errors="replace"),
            keyid=self.fingerprint,
            passphrase="",
        )
        return str(signed)

    async def _verify_gpg(self, data: bytes, signature: str) -> bool:
        """Verifica assinatura GPG real."""
        import gnupg

        gpg = gnupg.GPG(gnupghome=self._gpg_home)
        verified = await asyncio.to_thread(gpg.verify, signature)
        return bool(verified)

    @classmethod
    async def from_public_key(cls, agent_name: str, public_key: str) -> KeyPair:
        """Cria KeyPair apenas com chave pública (para verificação)."""
        fingerprint = hashlib.sha256(public_key.encode()).hexdigest()[:40]
        return cls(
            agent_name=agent_name,
            fingerprint=fingerprint,
            public_key=public_key,
        )
