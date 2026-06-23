"""Runtime configuration for the Casper Hermes plugin."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_RPC_URL = "https://node.testnet.casper.network/rpc"
DEFAULT_CHAIN_NAME = "casper-test"


@dataclass(frozen=True)
class CasperConfig:
    node_url: str
    api_key: str | None
    chain_name: str
    signing_key_hex: str | None
    signing_key_pem: str | None


def load_config() -> CasperConfig:
    node_url = (
        os.environ.get("CASPER_NODE_URL")
        or os.environ.get("CASPER_RPC_URL")
        or DEFAULT_RPC_URL
    )
    return CasperConfig(
        node_url=node_url.rstrip("/"),
        api_key=os.environ.get("CASPER_API_KEY") or None,
        chain_name=os.environ.get("CASPER_CHAIN_NAME") or DEFAULT_CHAIN_NAME,
        signing_key_hex=(
            os.environ.get("CASPER_SIGNING_KEY_HEX")
            or os.environ.get("CASPER_PRIVATE_KEY")
            or None
        ),
        signing_key_pem=os.environ.get("CASPER_SIGNING_KEY_PEM") or None,
    )


def is_signing_configured(cfg: CasperConfig | None = None) -> bool:
    cfg = cfg or load_config()
    return bool(cfg.signing_key_hex or cfg.signing_key_pem)
