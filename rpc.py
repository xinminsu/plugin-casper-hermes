"""Casper JSON-RPC client (read-only operations)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from config import CasperConfig, load_config
from utils import (
    motes_to_cspr,
    normalize_contract_hash,
    validate_account_hash,
    validate_public_key,
)

DEFAULT_TIMEOUT = 20


class CasperRpcError(Exception):
    pass


class CasperRpcClient:
    def __init__(self, config: CasperConfig | None = None) -> None:
        self.config = config or load_config()
        self.rpc_url = self.config.node_url
        if not self.rpc_url.endswith("/rpc"):
            self.rpc_url = f"{self.rpc_url.rstrip('/')}/rpc"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = self.config.api_key
        return headers

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        payload = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.rpc_url,
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise CasperRpcError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise CasperRpcError(f"Connection failed to {self.rpc_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise CasperRpcError(f"Request timeout after {DEFAULT_TIMEOUT}s") from exc

        if "error" in body:
            err = body["error"]
            raise CasperRpcError(f"RPC Error: {err.get('message', err)} (code: {err.get('code')})")
        return body.get("result")

    # --- Info API ---

    def get_node_status(self) -> dict[str, Any]:
        return self.call("info_get_status")

    def get_peers(self) -> dict[str, Any]:
        return self.call("info_get_peers")

    def get_deploy(self, deploy_hash: str) -> dict[str, Any]:
        return self.call("info_get_deploy", {"deploy_hash": deploy_hash})

    def get_chainspec(self) -> dict[str, Any]:
        return self.call("info_get_chainspec")

    def get_validator_changes(self) -> dict[str, Any]:
        return self.call("info_get_validator_changes")

    # --- Chain API ---

    def get_block_by_hash(self, block_hash: str) -> dict[str, Any]:
        return self.call("chain_get_block", {"block_identifier": {"Hash": block_hash}})

    def get_block_by_height(self, height: int) -> dict[str, Any]:
        return self.call("chain_get_block", {"block_identifier": {"Height": height}})

    def get_latest_block(self) -> dict[str, Any]:
        status = self.get_node_status()
        height = status.get("last_added_block_info", {}).get("height")
        if height is None:
            raise CasperRpcError("Could not determine latest block height")
        return self.get_block_by_height(int(height))

    def get_block_transfers(self, block_hash: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if block_hash:
            params["block_identifier"] = {"Hash": block_hash}
        return self.call("chain_get_block_transfers", params)

    def get_state_root_hash(self, height: int | None = None) -> str:
        params: dict[str, Any] = {}
        if height is not None:
            params["block_identifier"] = {"Height": height}
        result = self.call("chain_get_state_root_hash", params)
        return result["state_root_hash"]

    def get_era_summary(self, block_hash: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if block_hash:
            params["block_identifier"] = {"Hash": block_hash}
        return self.call("chain_get_era_summary", params)

    def get_era_validators(self, block_hash: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if block_hash:
            params["block_identifier"] = {"Hash": block_hash}
        return self.call("chain_get_era_validators", params)

    # --- State API ---

    def get_account_info(self, public_key: str) -> dict[str, Any]:
        return self.call("state_get_account_info", {"public_key": public_key})

    def get_account_info_by_hash(self, account_hash: str) -> dict[str, Any]:
        clean = account_hash.lower().replace("account-hash-", "")
        return self.call(
            "state_get_account_info",
            {"account_identifier": {"AccountHash": clean}},
        )

    def get_balance(self, purse_uref: str, state_root_hash: str | None = None) -> str:
        state_root = state_root_hash or self.get_state_root_hash()
        result = self.call(
            "state_get_balance",
            {"state_root_hash": state_root, "purse_uref": purse_uref},
        )
        return str(result["balance_value"])

    def get_contract_info(self, contract_hash: str, state_root_hash: str | None = None) -> dict[str, Any]:
        state_root = state_root_hash or self.get_state_root_hash()
        clean = normalize_contract_hash(contract_hash)
        return self.call(
            "state_get_contract",
            {"state_root_hash": state_root, "contract_hash": clean},
        )

    def get_dictionary_item(
        self,
        uref: str,
        dictionary_key: str,
        state_root_hash: str | None = None,
    ) -> dict[str, Any]:
        state_root = state_root_hash or self.get_state_root_hash()
        return self.call(
            "state_get_dictionary_item",
            {
                "state_root_hash": state_root,
                "dictionary_identifier": {"URef": {"uref": uref, "dictionary_key": dictionary_key}},
            },
        )

    def query_global_state(
        self,
        key: str,
        path: list[str] | None = None,
        state_root_hash: str | None = None,
    ) -> dict[str, Any]:
        state_root = state_root_hash or self.get_state_root_hash()
        return self.call(
            "query_global_state",
            {
                "state_identifier": {"StateRootHash": state_root},
                "key": key,
                "path": path or [],
            },
        )

    def get_state_item(
        self,
        key: str,
        path: list[str] | None = None,
        state_root_hash: str | None = None,
    ) -> dict[str, Any]:
        state_root = state_root_hash or self.get_state_root_hash()
        return self.call(
            "state_get_item",
            {"state_root_hash": state_root, "key": key, "path": path or []},
        )

    def get_auction_info(self, block_hash: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if block_hash:
            params["block_identifier"] = {"Hash": block_hash}
        return self.call("state_get_auction_info", params)

    def get_delegation_info(self, delegator_public_key: str, block_hash: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"delegator_public_key": delegator_public_key}
        if block_hash:
            params["block_identifier"] = {"Hash": block_hash}
        return self.call("state_get_auction_info", params)

    # --- High-level helpers ---

    def get_purse_balance_details(self, purse_uref: str, state_root_hash: str | None = None) -> dict[str, Any]:
        state_root = state_root_hash or self.get_state_root_hash()
        result = self.call(
            "state_get_balance",
            {"state_root_hash": state_root, "purse_uref": purse_uref},
        )
        return {
            "purse_uref": purse_uref,
            "balance_motes": str(result.get("balance_value", 0)),
            "balance_cspr": motes_to_cspr(str(result.get("balance_value", 0))),
            "state_root_hash": state_root,
            "proof": result.get("proof"),
            "api_version": result.get("api_version"),
        }

    def estimate_transaction_cost(self, payment_motes: str, is_module_bytes: bool = False) -> dict[str, Any]:
        return self.call(
            "chain_estimate_transaction_cost",
            {"deployment_cost": payment_motes, "is_module_bytes": is_module_bytes},
        )

    def resolve_account_info(self, address: str) -> dict[str, Any]:
        from utils import resolve_address_input

        kind, clean = resolve_address_input(address)
        if kind == "public_key":
            return self.get_account_info(clean)
        return self.get_account_info_by_hash(clean)

    def get_cspr_balance(self, address: str) -> dict[str, str]:
        account_info = self.resolve_account_info(address)
        account = account_info.get("account")
        if not account:
            raise CasperRpcError(
                f"Account not found on Casper network (RPC: {self.rpc_url}). "
                "Verify at https://testnet.cspr.live/"
            )
        main_purse = account["main_purse"]
        balance_motes = self.get_balance(main_purse)
        return {
            "address": address,
            "main_purse": main_purse,
            "balance_motes": balance_motes,
            "balance_cspr": motes_to_cspr(balance_motes),
        }

    def get_account_details(self, address: str) -> dict[str, Any]:
        account_info = self.resolve_account_info(address)
        account = account_info.get("account")
        if not account:
            raise CasperRpcError("Account not found")
        balance_motes = self.get_balance(account["main_purse"])
        return {
            "account_hash": account.get("account_hash", "N/A"),
            "main_purse": account["main_purse"],
            "balance_cspr": motes_to_cspr(balance_motes),
            "balance_motes": balance_motes,
            "named_keys": account.get("named_keys", []),
            "associated_keys": account.get("associated_keys", []),
            "action_thresholds": account.get("action_thresholds", {}),
        }

    def get_account_named_keys(self, public_key: str) -> list[dict[str, Any]]:
        account_info = self.get_account_info(public_key)
        return account_info.get("account", {}).get("named_keys", [])

    def get_contract_entry_points(self, contract_hash: str) -> list[dict[str, Any]]:
        info = self.get_contract_info(contract_hash)
        return info.get("contract", {}).get("entry_points", [])

    def get_dictionary_item_by_account(
        self,
        public_key: str,
        named_key: str,
        dictionary_key: str,
    ) -> dict[str, Any]:
        named_keys = self.get_account_named_keys(public_key)
        entry = next((nk for nk in named_keys if nk.get("name") == named_key), None)
        if not entry:
            raise CasperRpcError(f'Named key "{named_key}" not found in account')
        return self.get_dictionary_item(entry["key"], dictionary_key)

    def get_dictionary_item_by_contract(
        self,
        contract_hash: str,
        named_key: str,
        dictionary_key: str,
    ) -> dict[str, Any]:
        info = self.get_contract_info(contract_hash)
        named_keys = info.get("contract", {}).get("named_keys", [])
        entry = next((nk for nk in named_keys if nk.get("name") == named_key), None)
        if not entry:
            raise CasperRpcError(f'Named key "{named_key}" not found in contract')
        return self.get_dictionary_item(entry["key"], dictionary_key)
