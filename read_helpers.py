"""Shared read helpers for Casper contract/token/DApp queries."""

from __future__ import annotations

from typing import Any

try:
    from .rpc import CasperRpcClient
    from .utils import parse_cl_value, validate_public_key
except ImportError:
    from rpc import CasperRpcClient
    from utils import parse_cl_value, validate_public_key


def get_named_key_uref(client: CasperRpcClient, contract_hash: str, names: list[str]) -> str | None:
    info = client.get_contract_info(contract_hash)
    named_keys = info.get("contract", {}).get("named_keys", [])
    for name in names:
        for entry in named_keys:
            if entry.get("name") == name:
                return entry.get("key")
    return None


def account_dict_key(client: CasperRpcClient, public_key: str) -> str:
    account_info = client.get_account_info(public_key)
    account_hash = account_info.get("account", {}).get("account_hash", "")
    return account_hash.replace("account-hash-", "")


def list_contract_named_keys(client: CasperRpcClient, contract_hash: str) -> list[dict[str, Any]]:
    info = client.get_contract_info(contract_hash)
    return info.get("contract", {}).get("named_keys", [])
