"""Wallet generation (optional pycspr)."""

from __future__ import annotations

from typing import Any


class CasperTransactionError(Exception):
    pass


def _require_pycspr():
    try:
        import pycspr  # noqa: F401
    except ImportError as exc:
        raise CasperTransactionError(
            "pycspr is required for wallet generation. Install with: pip install pycspr"
        ) from exc


def generate_wallet() -> dict[str, Any]:
    _require_pycspr()
    import pycspr
    from pycspr.types.crypto import KeyAlgorithm

    private_key = pycspr.types.crypto.PrivateKey.generate(KeyAlgorithm.ED25519)
    public_key = private_key.public_key
    account_hash = public_key.account_hash.hex()

    return {
        "public_key": public_key.hex(),
        "private_key_hex": private_key.hex(),
        "account_hash": f"account-hash-{account_hash}",
        "warning": "Store the private key securely. Never share it in chat.",
    }
