#!/usr/bin/env python3
"""Standalone CLI for Casper blockchain queries (Hermes skill helper)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rpc import CasperRpcClient, CasperRpcError  # noqa: E402
from utils import format_timestamp, motes_to_cspr, truncate  # noqa: E402


def cmd_balance(args: argparse.Namespace) -> int:
    client = CasperRpcClient()
    result = client.get_cspr_balance(args.address)
    print(f"Balance: {result['balance_cspr']} CSPR")
    print(f"Main purse: {result['main_purse']}")
    return 0


def cmd_account(args: argparse.Namespace) -> int:
    client = CasperRpcClient()
    details = client.get_account_details(args.address)
    print(json.dumps(details, indent=2))
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    client = CasperRpcClient()
    status = client.get_node_status()
    last = status.get("last_added_block_info", {})
    print(f"Chain: {status.get('chainspec_name', 'N/A')}")
    print(f"API version: {status.get('api_version', 'N/A')}")
    print(f"Peers: {len(status.get('peers', []))}")
    print(f"Last block height: {last.get('height', 'N/A')}")
    print(f"Last block time: {format_timestamp(last.get('timestamp'))}")
    return 0


def cmd_block(args: argparse.Namespace) -> int:
    client = CasperRpcClient()
    if args.latest:
        result = client.get_latest_block()
    elif args.height is not None:
        result = client.get_block_by_height(args.height)
    elif args.hash:
        result = client.get_block_by_hash(args.hash)
    else:
        result = client.get_latest_block()
    block = result.get("block", {})
    header = block.get("header", {})
    print(f"Hash: {block.get('hash', 'N/A')}")
    print(f"Height: {header.get('height', 'N/A')}")
    print(f"Era: {header.get('era_id', 'N/A')}")
    print(f"Timestamp: {format_timestamp(header.get('timestamp'))}")
    return 0


def cmd_deploy(args: argparse.Namespace) -> int:
    client = CasperRpcClient()
    result = client.get_deploy(args.hash)
    deploy = result.get("deploy", {})
    header = deploy.get("header", {})
    exec_results = result.get("execution_results", [])
    exec_result = exec_results[0].get("result") if exec_results else {}
    status = "pending"
    if exec_result.get("Success"):
        status = "success"
    elif exec_result.get("Failure"):
        status = "failed"
    print(f"Deploy: {args.hash}")
    print(f"Account: {truncate(header.get('account', ''), 40)}")
    print(f"Chain: {header.get('chain_name', 'N/A')}")
    print(f"Status: {status}")
    return 0


def cmd_validators(_args: argparse.Namespace) -> int:
    client = CasperRpcClient()
    result = client.get_auction_info()
    auction = result.get("auction_state", {})
    bids = auction.get("bids", [])
    active = [b for b in bids if b.get("bid") and not b["bid"].get("inactive")]
    top = sorted(
        active,
        key=lambda b: int(b.get("bid", {}).get("staked_amount", 0)),
        reverse=True,
    )[:10]
    print(f"Era: {auction.get('era_id', 'N/A')}")
    print(f"Active validators: {len(active)}")
    for i, v in enumerate(top, 1):
        stake = motes_to_cspr(v.get("bid", {}).get("staked_amount", 0))
        print(f"{i}. {truncate(v.get('public_key', ''), 30)} — {stake} CSPR")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Casper blockchain CLI for Hermes")
    sub = parser.add_subparsers(dest="command", required=True)

    p_balance = sub.add_parser("balance", help="Get CSPR balance")
    p_balance.add_argument("address", help="Public key or account hash")
    p_balance.set_defaults(func=cmd_balance)

    p_account = sub.add_parser("account", help="Get account details")
    p_account.add_argument("address", help="Public key or account hash")
    p_account.set_defaults(func=cmd_account)

    p_status = sub.add_parser("status", help="Get node status")
    p_status.set_defaults(func=cmd_status)

    p_block = sub.add_parser("block", help="Get block info")
    p_block.add_argument("--latest", action="store_true", help="Latest block")
    p_block.add_argument("--height", type=int, help="Block height")
    p_block.add_argument("--hash", help="Block hash")
    p_block.set_defaults(func=cmd_block)

    p_deploy = sub.add_parser("deploy", help="Get deploy status")
    p_deploy.add_argument("hash", help="Deploy hash")
    p_deploy.set_defaults(func=cmd_deploy)

    p_validators = sub.add_parser("validators", help="List top validators")
    p_validators.set_defaults(func=cmd_validators)

    args = parser.parse_args()
    try:
        return args.func(args)
    except CasperRpcError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
