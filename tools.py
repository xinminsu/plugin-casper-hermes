"""Tool handlers for the Casper Hermes plugin."""

from __future__ import annotations

import json
from typing import Any

from alerts import add_alert, check_alerts, list_alerts, remove_alert
from config import load_config
from read_helpers import list_contract_named_keys
from reads import dapp_read, query_gas, staking_read, token_read
from rpc import CasperRpcClient, CasperRpcError
from transaction import CasperTransactionError, generate_wallet
from tx_service import CasperTransactionError as TxBridgeError
from tx_service import run_tx_operation, transfer_cspr
from utils import (
    format_timestamp,
    motes_to_cspr,
    normalize_address,
    parse_cl_value,
    truncate,
    validate_address,
    validate_contract_hash,
    validate_public_key,
)


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps(payload)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra})


def _client() -> CasperRpcClient:
    return CasperRpcClient(config=load_config())


def _write_error(exc: Exception) -> str:
    return _err(str(exc))


# ---------------------------------------------------------------------------
# Read handlers
# ---------------------------------------------------------------------------

def casper_get_balance(args: dict, **kwargs) -> str:
    address = normalize_address((args.get("address") or "").strip())
    if not address:
        return _err("address is required")
    if not validate_address(address):
        return _err("Invalid address (public key, account hash, or 0x hex)")
    try:
        result = _client().get_cspr_balance(address)
        result["note"] = "CEP-18 token balances use casper_token_read with query_type balance_of"
        return _ok(result)
    except CasperRpcError as exc:
        return _err(str(exc))


def casper_account_read(args: dict, **kwargs) -> str:
    query_type = (args.get("query_type") or "").strip()
    client = _client()
    try:
        if query_type == "account_info":
            address = normalize_address((args.get("address") or args.get("public_key") or "").strip())
            if not validate_address(address):
                return _err("address required")
            return _ok(client.get_account_details(address))

        if query_type == "named_keys":
            pub = (args.get("public_key") or args.get("address") or "").strip()
            if not validate_public_key(normalize_address(pub)):
                return _err("public_key required")
            return _ok({"named_keys": client.get_account_named_keys(normalize_address(pub))})

        if query_type == "purse_balance":
            uref = (args.get("uref") or "").strip()
            if not uref:
                return _err("uref required")
            return _ok(client.get_purse_balance_details(uref))

        if query_type == "contract_info":
            ch = (args.get("contract_hash") or "").strip()
            if not validate_contract_hash(ch):
                return _err("contract_hash required")
            info = client.get_contract_info(ch)
            contract = info.get("contract", {})
            return _ok(
                {
                    "contract_hash": contract.get("contract_hash"),
                    "package_hash": contract.get("contract_package_hash"),
                    "version": contract.get("contract_version"),
                    "entry_point_count": len(contract.get("entry_points", [])),
                }
            )

        if query_type == "contract_named_keys":
            ch = (args.get("contract_hash") or "").strip()
            if not validate_contract_hash(ch):
                return _err("contract_hash required")
            return _ok({"named_keys": list_contract_named_keys(client, ch)})

        if query_type == "entry_points":
            ch = (args.get("contract_hash") or "").strip()
            if not validate_contract_hash(ch):
                return _err("contract_hash required")
            eps = client.get_contract_entry_points(ch)
            return _ok(
                {
                    "entry_points": [
                        {
                            "name": ep.get("name"),
                            "type": ep.get("entry_point_type"),
                            "args": [{"name": a.get("name"), "cl_type": a.get("cl_type")} for a in ep.get("args", [])],
                        }
                        for ep in eps
                    ]
                }
            )

        if query_type == "dictionary_item":
            uref = (args.get("uref") or "").strip()
            dk = (args.get("dictionary_key") or "").strip()
            if not uref or not dk:
                return _err("uref and dictionary_key required")
            result = client.get_dictionary_item(uref, dk)
            stored = result.get("stored_value", {})
            cl = stored.get("CLValue") or stored.get("cl_value")
            return _ok({"value": parse_cl_value(cl)})

        if query_type == "dictionary_by_account":
            pk = (args.get("public_key") or "").strip()
            nk = (args.get("named_key") or "").strip()
            dk = (args.get("dictionary_key") or "").strip()
            if not all([pk, nk, dk]):
                return _err("public_key, named_key, dictionary_key required")
            result = client.get_dictionary_item_by_account(pk, nk, dk)
            stored = result.get("stored_value", {})
            cl = stored.get("CLValue") or stored.get("cl_value")
            return _ok({"value": parse_cl_value(cl)})

        if query_type == "dictionary_by_contract":
            ch = (args.get("contract_hash") or "").strip()
            nk = (args.get("named_key") or "").strip()
            dk = (args.get("dictionary_key") or "").strip()
            if not all([ch, nk, dk]):
                return _err("contract_hash, named_key, dictionary_key required")
            result = client.get_dictionary_item_by_contract(ch, nk, dk)
            stored = result.get("stored_value", {})
            cl = stored.get("CLValue") or stored.get("cl_value")
            return _ok({"value": parse_cl_value(cl)})

        if query_type == "global_state":
            key = (args.get("key") or args.get("uref") or "").strip()
            path = args.get("path") or []
            if not key:
                return _err("key or uref required")
            result = client.query_global_state(key, path)
            stored = result.get("stored_value", {})
            if stored.get("CLValue"):
                value = parse_cl_value(stored["CLValue"])
            elif stored.get("Account"):
                value = f"Account: {truncate(stored['Account'].get('account_hash'), 30)}"
            elif stored.get("Contract"):
                value = f"Contract: {truncate(stored['Contract'].get('contract_hash'), 30)}"
            else:
                value = truncate(json.dumps(stored), 200)
            return _ok({"block_hash": result.get("block_hash"), "value": value})

        if query_type == "state_item":
            key = (args.get("key") or args.get("uref") or "").strip()
            path = args.get("path") or []
            if not key:
                return _err("key required")
            result = client.get_state_item(key, path)
            stored = result.get("stored_value", {})
            cl = stored.get("CLValue") or stored.get("cl_value")
            return _ok({"block_hash": result.get("block_hash"), "value": parse_cl_value(cl) if cl else json.dumps(stored)})

        return _err(f"Unknown query_type: {query_type}")
    except CasperRpcError as exc:
        return _err(str(exc))


def casper_network_query(args: dict, **kwargs) -> str:
    query_type = (args.get("query_type") or "").strip()
    client = _client()
    try:
        if query_type == "node_status":
            status = client.get_node_status()
            last = status.get("last_added_block_info", {})
            return _ok(
                {
                    "chainspec_name": status.get("chainspec_name"),
                    "api_version": status.get("api_version"),
                    "peer_count": len(status.get("peers", [])),
                    "last_block_height": last.get("height"),
                    "last_block_timestamp": format_timestamp(last.get("timestamp")),
                }
            )
        if query_type == "peers":
            result = client.get_peers()
            peers = result.get("peers", [])
            return _ok({"peer_count": len(peers), "peers": peers[:20]})
        if query_type == "latest_block":
            result = client.get_latest_block()
            block = result.get("block", {})
            header = block.get("header", {})
            body = block.get("body", {})
            return _ok(
                {
                    "hash": block.get("hash"),
                    "height": header.get("height"),
                    "era_id": header.get("era_id"),
                    "timestamp": format_timestamp(header.get("timestamp")),
                    "deploy_count": len(body.get("deploy_hashes", [])),
                }
            )
        if query_type == "block_by_height":
            height = args.get("block_height")
            if height is None:
                return _err("block_height required")
            result = client.get_block_by_height(int(height))
            block = result.get("block", {})
            header = block.get("header", {})
            return _ok({"hash": block.get("hash"), "height": header.get("height"), "era_id": header.get("era_id")})
        if query_type == "block_by_hash":
            bh = (args.get("block_hash") or "").strip()
            if not bh:
                return _err("block_hash required")
            result = client.get_block_by_hash(bh)
            block = result.get("block", {})
            header = block.get("header", {})
            return _ok({"hash": block.get("hash"), "height": header.get("height"), "era_id": header.get("era_id")})
        if query_type == "era_summary":
            result = client.get_era_summary()
            era = result.get("era_summary", {})
            rewards = era.get("seigniorage_allocations", [])
            total = sum(int(r.get("amount", 0)) for r in rewards)
            return _ok({"era_id": era.get("era_id"), "total_rewards_cspr": motes_to_cspr(total), "reward_recipients": len(rewards)})
        if query_type == "validators":
            result = client.get_auction_info()
            auction = result.get("auction_state", {})
            bids = auction.get("bids", [])
            active = [b for b in bids if b.get("bid") and not b["bid"].get("inactive")]
            top = sorted(active, key=lambda b: int(b.get("bid", {}).get("staked_amount", 0)), reverse=True)[:10]
            return _ok(
                {
                    "era_id": auction.get("era_id"),
                    "active_bids": len(active),
                    "top_validators": [
                        {"public_key": truncate(v.get("public_key"), 30), "staked_cspr": motes_to_cspr(v.get("bid", {}).get("staked_amount", 0))}
                        for v in top
                    ],
                }
            )
        if query_type == "transfers":
            bh = (args.get("block_hash") or "").strip() or None
            result = client.get_block_transfers(bh)
            transfers = result.get("transfers", [])
            return _ok(
                {
                    "block_hash": result.get("block_hash"),
                    "transfer_count": len(transfers),
                    "transfers": [
                        {"from": truncate(t.get("from"), 25), "to": truncate(t.get("to"), 25), "amount_cspr": motes_to_cspr(t.get("amount", 0))}
                        for t in transfers[:10]
                    ],
                }
            )
        if query_type == "state_root_hash":
            return _ok({"state_root_hash": client.get_state_root_hash()})
        if query_type == "chainspec":
            return _ok(client.get_chainspec())
        return _err(f"Unknown query_type: {query_type}")
    except CasperRpcError as exc:
        return _err(str(exc))


def casper_gas_query(args: dict, **kwargs) -> str:
    client = _client()
    query_type = args.get("query_type") or "gas_info"
    try:
        if query_type == "gas_info":
            return _ok(query_gas(client))
        if query_type == "estimate_cost":
            payment = args.get("payment_motes") or "2500000000"
            is_module = bool(args.get("is_module_bytes"))
            return _ok(client.estimate_transaction_cost(str(payment), is_module))
        return _err(f"Unknown query_type: {query_type}")
    except CasperRpcError as exc:
        return _err(str(exc))


def casper_token_read(args: dict, **kwargs) -> str:
    query_type = (args.get("query_type") or "").strip()
    contract_hash = (args.get("contract_hash") or "").strip()
    if not validate_contract_hash(contract_hash):
        return _err("contract_hash required")
    try:
        params = {k: v for k, v in args.items() if k not in ("query_type", "contract_hash") and v is not None}
        return _ok(token_read(_client(), query_type, contract_hash, **params))
    except (CasperRpcError, ValueError) as exc:
        return _err(str(exc))


def casper_staking_read(args: dict, **kwargs) -> str:
    query_type = (args.get("query_type") or "").strip()
    client = _client()
    try:
        if query_type in ("validator_detail", "delegation"):
            return _ok(staking_read(client, query_type, public_key=args.get("public_key")))
        if query_type == "era_validators":
            result = client.get_era_validators()
            weights = []
            for ev in result.get("era_validators", []):
                for vw in ev.get("validator_weights", []):
                    weights.append({"public_key": truncate(vw.get("public_key"), 30), "weight_cspr": motes_to_cspr(vw.get("weight", 0))})
            weights.sort(key=lambda w: float(w["weight_cspr"]), reverse=True)
            return _ok({"era_id": result.get("era_id"), "validators": weights[:15]})
        if query_type == "auction_info":
            result = client.get_auction_info()
            auction = result.get("auction_state", {})
            bids = auction.get("bids", [])
            active = [b for b in bids if b.get("bid") and not b["bid"].get("inactive")]
            total = sum(int(b.get("bid", {}).get("staked_amount", 0)) for b in active)
            return _ok({"era_id": auction.get("era_id"), "total_bids": len(bids), "active_bids": len(active), "total_staked_cspr": motes_to_cspr(total)})
        if query_type == "validator_changes":
            return _ok(client.get_validator_changes())
        if query_type == "era_summary":
            result = client.get_era_summary()
            era = result.get("era_summary", {})
            rewards = era.get("seigniorage_allocations", [])
            total = sum(int(r.get("amount", 0)) for r in rewards)
            return _ok({"era_id": era.get("era_id"), "total_rewards_cspr": motes_to_cspr(total), "reward_recipients": len(rewards)})
        return _err(f"Unknown query_type: {query_type}")
    except (CasperRpcError, ValueError) as exc:
        return _err(str(exc))


def casper_dapp_read(args: dict, **kwargs) -> str:
    query_type = (args.get("query_type") or "").strip()
    contract_hash = (args.get("contract_hash") or "").strip()
    if not validate_contract_hash(contract_hash):
        return _err("contract_hash required")
    try:
        params = {k: v for k, v in args.items() if k not in ("query_type", "contract_hash") and v is not None}
        return _ok(dapp_read(_client(), query_type, contract_hash, **params))
    except (CasperRpcError, ValueError) as exc:
        return _err(str(exc))


def casper_deploy_status(args: dict, **kwargs) -> str:
    deploy_hash = (args.get("deploy_hash") or "").strip().lower().replace("deploy-hash-", "")
    if not deploy_hash:
        return _err("deploy_hash required")
    try:
        result = _client().get_deploy(deploy_hash)
        deploy = result.get("deploy", {})
        header = deploy.get("header", {})
        exec_results = result.get("execution_results", [])
        exec_result = exec_results[0].get("result") if exec_results else {}
        status = "pending"
        gas = None
        error_message = None
        if exec_result.get("Success"):
            status = "success"
            gas = exec_result["Success"].get("cost")
        elif exec_result.get("Failure"):
            status = "failed"
            error_message = exec_result["Failure"].get("error_message")
        return _ok(
            {
                "deploy_hash": deploy_hash,
                "account": header.get("account"),
                "timestamp": format_timestamp(header.get("timestamp")),
                "status": status,
                "gas_consumed": gas,
                "error_message": error_message,
            }
        )
    except CasperRpcError as exc:
        return _err(str(exc))


def casper_alerts(args: dict, **kwargs) -> str:
    action = (args.get("action") or "").strip()
    try:
        if action == "add":
            return _ok(
                add_alert(
                    alert_type=args.get("alert_type") or "custom",
                    address=args.get("address"),
                    threshold=args.get("threshold"),
                    message=args.get("message"),
                )
            )
        if action == "list":
            return _ok({"alerts": list_alerts()})
        if action == "remove":
            alert_id = (args.get("alert_id") or "").strip()
            if not alert_id:
                return _err("alert_id required")
            return _ok(remove_alert(alert_id))
        if action == "check":
            return _ok({"triggered": check_alerts(_client())})
        return _err(f"Unknown action: {action}")
    except ValueError as exc:
        return _err(str(exc))


def casper_generate_wallet(args: dict, **kwargs) -> str:
    try:
        return _ok(generate_wallet())
    except CasperTransactionError as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Write handlers
# ---------------------------------------------------------------------------

def _pick(args: dict, *keys: str) -> dict[str, Any]:
    return {k: args[k] for k in keys if k in args and args[k] is not None}


def casper_native_write(args: dict, **kwargs) -> str:
    op = (args.get("operation") or "").strip()
    op_map = {
        "transfer": "transfer",
        "create_purse": "create_purse",
        "add_associated_key": "add_associated_key",
        "remove_associated_key": "remove_associated_key",
        "set_action_threshold": "set_action_threshold",
        "put_named_key": "put_named_key",
    }
    if op not in op_map:
        return _err(f"Unknown operation: {op}")
    try:
        if op == "transfer":
            return _ok(transfer_cspr(args["to_public_key"], args["amount_cspr"]))
        params = dict(args)
        params.pop("operation", None)
        return _ok(run_tx_operation(op_map[op], params))
    except (TxBridgeError, CasperTransactionError) as exc:
        return _write_error(exc)


def casper_token_write(args: dict, **kwargs) -> str:
    op = (args.get("operation") or "").strip()
    op_map = {
        "mint": "cep18_mint",
        "burn": "cep18_burn",
        "transfer": "cep18_transfer",
        "approve": "cep18_approve",
        "increase_allowance": "cep18_increase_allowance",
        "decrease_allowance": "cep18_decrease_allowance",
        "transfer_from": "cep18_transfer_from",
    }
    if op not in op_map:
        return _err(f"Unknown operation: {op}")
    try:
        params = {"contract_hash": args["contract_hash"], **{k: args[k] for k in args if k not in ("operation",)}}
        return _ok(run_tx_operation(op_map[op], params))
    except TxBridgeError as exc:
        return _write_error(exc)


def casper_nft_write(args: dict, **kwargs) -> str:
    op = (args.get("operation") or "").strip()
    op_map = {
        "mint": "cep47_mint",
        "mint_copies": "cep47_mint_copies",
        "burn": "cep47_burn",
        "transfer": "cep47_transfer",
        "approve": "cep47_approve",
        "transfer_from": "cep47_transfer_from",
        "set_metadata": "cep78_set_metadata",
        "batch_transfer": "cep78_batch_transfer",
        "batch_burn": "cep78_batch_burn",
        "set_admin": "cep78_set_admin",
    }
    if op not in op_map:
        return _err(f"Unknown operation: {op}")
    try:
        params = {k: args[k] for k in args if k != "operation"}
        return _ok(run_tx_operation(op_map[op], params))
    except TxBridgeError as exc:
        return _write_error(exc)


def casper_staking_write(args: dict, **kwargs) -> str:
    op = (args.get("operation") or "").strip()
    op_map = {
        "bond": "bond",
        "delegate": "delegate",
        "unbond": "unbond",
        "undelegate": "undelegate",
        "withdraw_rewards": "withdraw_rewards",
        "set_commission_rate": "set_commission_rate",
    }
    if op not in op_map:
        return _err(f"Unknown operation: {op}")
    try:
        params = {k: args[k] for k in args if k != "operation"}
        return _ok(run_tx_operation(op_map[op], params))
    except TxBridgeError as exc:
        return _write_error(exc)


def casper_defi_write(args: dict, **kwargs) -> str:
    op = (args.get("operation") or "").strip()
    op_map = {
        "swap": "amm_swap",
        "add_liquidity": "add_liquidity",
        "remove_liquidity": "remove_liquidity",
        "stake_lp": "stake_lp",
        "claim_reward": "claim_reward",
        "create_order": "create_order",
        "cancel_order": "cancel_order",
    }
    if op not in op_map:
        return _err(f"Unknown operation: {op}")
    try:
        params = {k: args[k] for k in args if k != "operation"}
        return _ok(run_tx_operation(op_map[op], params))
    except TxBridgeError as exc:
        return _write_error(exc)


def casper_dapp_write(args: dict, **kwargs) -> str:
    op = (args.get("operation") or "").strip()
    op_map = {
        "counter_increment": "counter_increment",
        "counter_decrement": "counter_decrement",
        "dictionary_put": "dictionary_put",
        "dictionary_remove": "dictionary_remove",
        "create_proposal": "create_proposal",
        "cast_vote": "cast_vote",
        "execute_proposal": "execute_proposal",
        "save_asset_record": "save_asset_record",
        "call_contract": "call_contract",
    }
    if op not in op_map:
        return _err(f"Unknown operation: {op}")
    try:
        params = {k: args[k] for k in args if k != "operation"}
        if op == "call_contract" and "entry_point" in params:
            params.setdefault("args", params.get("args") or {})
        return _ok(run_tx_operation(op_map[op], params))
    except TxBridgeError as exc:
        return _write_error(exc)
