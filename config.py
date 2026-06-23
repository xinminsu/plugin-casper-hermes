"""Runtime configuration for the Casper Hermes plugin."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_RPC_URL = "https://node.testnet.casper.network/rpc"
DEFAULT_CHAIN_NAME = "casper-test"
DEFAULT_RPC_TIMEOUT = 45
DEFAULT_RPC_RETRIES = 2

NETWORK_PRESETS: dict[str, dict[str, str]] = {
    "testnet": {
        "node_url": "https://node.testnet.casper.network/rpc",
        "chain_name": "casper-test",
        "explorer": "https://testnet.cspr.live",
    },
    "casper-test": {
        "node_url": "https://node.testnet.casper.network/rpc",
        "chain_name": "casper-test",
        "explorer": "https://testnet.cspr.live",
    },
    "mainnet": {
        "node_url": "https://node.mainnet.casper.network/rpc",
        "chain_name": "casper",
        "explorer": "https://cspr.live",
    },
    "casper": {
        "node_url": "https://node.mainnet.casper.network/rpc",
        "chain_name": "casper",
        "explorer": "https://cspr.live",
    },
}


@dataclass(frozen=True)
class CasperConfig:
    node_url: str
    api_key: str | None
    chain_name: str
    network_label: str
    explorer_url: str
    signing_key_hex: str | None
    signing_key_pem: str | None
    rpc_timeout: int
    rpc_retries: int


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def resolve_network(network: str | None = None) -> tuple[str, str, str, str]:
    """Resolve (node_url, chain_name, network_label, explorer_url)."""
    if network:
        key = network.strip().lower()
        preset = NETWORK_PRESETS.get(key)
        if preset:
            label = "mainnet" if preset["chain_name"] == "casper" else "testnet"
            return preset["node_url"], preset["chain_name"], label, preset["explorer"]

    node_url = (
        os.environ.get("CASPER_NODE_URL")
        or os.environ.get("CASPER_RPC_URL")
        or DEFAULT_RPC_URL
    ).rstrip("/")
    chain_name = os.environ.get("CASPER_CHAIN_NAME") or DEFAULT_CHAIN_NAME
    label = "mainnet" if chain_name == "casper" else "testnet"
    explorer = NETWORK_PRESETS["mainnet" if label == "mainnet" else "testnet"]["explorer"]
    return node_url, chain_name, label, explorer


def load_config(network: str | None = None) -> CasperConfig:
    node_url, chain_name, network_label, explorer = resolve_network(network)
    return CasperConfig(
        node_url=node_url,
        api_key=os.environ.get("CASPER_API_KEY") or None,
        chain_name=chain_name,
        network_label=network_label,
        explorer_url=explorer,
        signing_key_hex=(
            os.environ.get("CASPER_SIGNING_KEY_HEX")
            or os.environ.get("CASPER_PRIVATE_KEY")
            or None
        ),
        signing_key_pem=os.environ.get("CASPER_SIGNING_KEY_PEM") or None,
        rpc_timeout=_int_env("CASPER_RPC_TIMEOUT", DEFAULT_RPC_TIMEOUT),
        rpc_retries=_int_env("CASPER_RPC_RETRIES", DEFAULT_RPC_RETRIES),
    )


def is_signing_configured(cfg: CasperConfig | None = None) -> bool:
    cfg = cfg or load_config()
    return bool(cfg.signing_key_hex or cfg.signing_key_pem)
