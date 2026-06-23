"""Casper blockchain read operations — tokens, NFTs, DApps, gas, staking."""

from __future__ import annotations

from typing import Any

try:
    from .read_helpers import account_dict_key, get_named_key_uref, list_contract_named_keys
    from .rpc import CasperRpcClient
    from .utils import motes_to_cspr, parse_cl_value, validate_public_key
except ImportError:
    from read_helpers import account_dict_key, get_named_key_uref, list_contract_named_keys
    from rpc import CasperRpcClient
    from utils import motes_to_cspr, parse_cl_value, validate_public_key


# ---------------------------------------------------------------------------
# Gas
# ---------------------------------------------------------------------------

def query_gas(client: CasperRpcClient, payment_motes: str = "2500000000", is_module_bytes: bool = False) -> dict[str, Any]:
    try:
        result = client.call(
            "chain_estimate_transaction_cost",
            {"deployment_cost": payment_motes, "is_module_bytes": is_module_bytes},
        )
        return {
            "gas_price": 1,
            "standard_transfer_cspr": "2.5",
            "standard_transfer_motes": "2500000000",
            "contract_call_cspr": "2.5",
            "contract_deploy_cspr": "10",
            "estimate": result,
        }
    except Exception:
        return {
            "gas_price": 1,
            "standard_transfer_cspr": "2.5",
            "standard_transfer_motes": "2500000000",
            "contract_call_cspr": "2.5",
            "contract_deploy_cspr": "10",
            "note": "Casper uses fixed gas price (1). Costs are predictable.",
        }


def estimate_transaction_cost(client: CasperRpcClient, payment_motes: str, is_module_bytes: bool = False) -> dict[str, Any]:
    result = client.call(
        "chain_estimate_transaction_cost",
        {"deployment_cost": payment_motes, "is_module_bytes": is_module_bytes},
    )
    return result


# ---------------------------------------------------------------------------
# Token / NFT reads (CEP-18 / CEP-47 / CEP-78)
# ---------------------------------------------------------------------------

def token_read(client: CasperRpcClient, query_type: str, contract_hash: str, **kwargs) -> dict[str, Any]:
    if query_type == "total_supply":
        uref = get_named_key_uref(client, contract_hash, ["total_supply", "total_supply_uref", "totalsupply"])
        if not uref:
            raise ValueError("Could not find total_supply named key")
        result = client.query_global_state(uref)
        return {"total_supply": parse_cl_value(result.get("stored_value", {}).get("CLValue"))}

    if query_type == "balance_of":
        owner = kwargs.get("owner") or kwargs.get("public_key")
        if not owner or not validate_public_key(owner):
            raise ValueError("owner public key required (68 hex)")
        balances_uref = get_named_key_uref(client, contract_hash, ["balances", "balances_uref", "balance"])
        if not balances_uref:
            raise ValueError("Could not find balances named key")
        dict_key = account_dict_key(client, owner)
        result = client.get_dictionary_item(balances_uref, dict_key)
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"owner": owner, "balance": parse_cl_value(cl)}

    if query_type == "allowance":
        owner = kwargs.get("owner")
        spender = kwargs.get("spender")
        if not owner or not spender:
            raise ValueError("owner and spender public keys required")
        allowances_uref = get_named_key_uref(client, contract_hash, ["allowances", "allowances_uref", "allowance"])
        if not allowances_uref:
            raise ValueError("Could not find allowances named key")
        owner_hash = account_dict_key(client, owner)
        spender_hash = account_dict_key(client, spender)
        result = client.get_dictionary_item(allowances_uref, owner_hash + spender_hash)
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"owner": owner, "spender": spender, "allowance": parse_cl_value(cl)}

    if query_type == "metadata":
        named_keys = list_contract_named_keys(client, contract_hash)
        meta: dict[str, str] = {"name": "N/A", "symbol": "N/A", "decimals": "N/A"}
        for field, candidates in [
            ("name", ["name", "token_name"]),
            ("symbol", ["symbol", "token_symbol"]),
            ("decimals", ["decimals", "token_decimals"]),
        ]:
            entry = next((nk for nk in named_keys if nk.get("name") in candidates), None)
            if entry:
                try:
                    r = client.query_global_state(entry["key"])
                    meta[field] = parse_cl_value(r.get("stored_value", {}).get("CLValue"))
                except Exception:
                    pass
        return meta

    if query_type == "nft_total_supply":
        uref = get_named_key_uref(
            client, contract_hash, ["total_supply", "minted_tokens", "number_of_minted_tokens", "count"]
        )
        if not uref:
            raise ValueError("Could not find NFT total supply key")
        result = client.query_global_state(uref)
        return {"total_supply": parse_cl_value(result.get("stored_value", {}).get("CLValue"))}

    if query_type == "nft_owner_of":
        token_id = kwargs.get("token_id")
        if not token_id:
            raise ValueError("token_id required")
        owners_uref = get_named_key_uref(
            client, contract_hash, ["owners", "token_owners", "account_by_id", "metadata_owners"]
        )
        if not owners_uref:
            raise ValueError("Could not find owners named key")
        result = client.get_dictionary_item(owners_uref, str(token_id))
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"token_id": token_id, "owner": parse_cl_value(cl)}

    if query_type == "nft_tokens_of":
        owner = kwargs.get("owner")
        if not owner or not validate_public_key(owner):
            raise ValueError("owner public key required")
        owned_uref = get_named_key_uref(
            client, contract_hash, ["owned_tokens", "account_owned_tokens", "token_owners_reverse"]
        )
        if not owned_uref:
            raise ValueError("Could not find owned_tokens key")
        dict_key = account_dict_key(client, owner)
        result = client.get_dictionary_item(owned_uref, dict_key)
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"owner": owner, "tokens": parse_cl_value(cl)}

    if query_type == "nft_metadata":
        token_id = kwargs.get("token_id")
        if not token_id:
            raise ValueError("token_id required")
        metadata_uref = get_named_key_uref(
            client, contract_hash, ["metadata", "token_metadata", "metadata_by_id", "cep78_metadata"]
        )
        if not metadata_uref:
            raise ValueError("Could not find metadata key")
        result = client.get_dictionary_item(metadata_uref, str(token_id))
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"token_id": token_id, "metadata": parse_cl_value(cl)}

    if query_type == "nft_approved":
        token_id = kwargs.get("token_id")
        if not token_id:
            raise ValueError("token_id required")
        approvals_uref = get_named_key_uref(client, contract_hash, ["approvals", "token_approvals", "approved"])
        if not approvals_uref:
            raise ValueError("Could not find approvals key")
        result = client.get_dictionary_item(approvals_uref, str(token_id))
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"token_id": token_id, "approved": parse_cl_value(cl)}

    if query_type == "nft_max_supply":
        uref = get_named_key_uref(
            client, contract_hash, ["max_supply", "collection_max_supply", "max_total_supply"]
        )
        if not uref:
            raise ValueError("Could not find max_supply key")
        result = client.query_global_state(uref)
        return {"max_supply": parse_cl_value(result.get("stored_value", {}).get("CLValue"))}

    if query_type == "nft_batch_owners":
        token_ids = kwargs.get("token_ids") or []
        if not token_ids:
            raise ValueError("token_ids list required")
        owners_uref = get_named_key_uref(client, contract_hash, ["owners", "token_owners", "account_by_id"])
        if not owners_uref:
            raise ValueError("Could not find owners key")
        results = []
        for tid in token_ids[:10]:
            try:
                r = client.get_dictionary_item(owners_uref, str(tid))
                stored = r.get("stored_value", {})
                cl = stored.get("CLValue") or stored.get("cl_value")
                results.append({"token_id": tid, "owner": parse_cl_value(cl)})
            except Exception:
                results.append({"token_id": tid, "owner": "Not found"})
        return {"results": results}

    raise ValueError(f"Unknown token query_type: {query_type}")


# ---------------------------------------------------------------------------
# DApp reads
# ---------------------------------------------------------------------------

def dapp_read(client: CasperRpcClient, query_type: str, contract_hash: str, **kwargs) -> dict[str, Any]:
    if query_type == "counter_value":
        uref = get_named_key_uref(client, contract_hash, ["count", "counter", "value", "counter_value"])
        if not uref:
            raise ValueError("Could not find counter key")
        result = client.query_global_state(uref)
        return {"count": parse_cl_value(result.get("stored_value", {}).get("CLValue"))}

    if query_type == "amm_reserves":
        reserve_a = get_named_key_uref(client, contract_hash, ["reserve_a", "token_a_reserve", "reserve0", "reserve_0"])
        reserve_b = get_named_key_uref(client, contract_hash, ["reserve_b", "token_b_reserve", "reserve1", "reserve_1"])
        lp_supply = get_named_key_uref(client, contract_hash, ["lp_token_supply", "total_lp", "total_supply"])
        out: dict[str, Any] = {"reserve_a": "N/A", "reserve_b": "N/A", "lp_supply": "N/A"}
        if reserve_a:
            r = client.query_global_state(reserve_a)
            out["reserve_a"] = parse_cl_value(r.get("stored_value", {}).get("CLValue"))
        if reserve_b:
            r = client.query_global_state(reserve_b)
            out["reserve_b"] = parse_cl_value(r.get("stored_value", {}).get("CLValue"))
        if lp_supply:
            r = client.query_global_state(lp_supply)
            out["lp_supply"] = parse_cl_value(r.get("stored_value", {}).get("CLValue"))
        return out

    if query_type == "amm_lp_balance":
        user = kwargs.get("public_key")
        if not user or not validate_public_key(user):
            raise ValueError("public_key required")
        balances_uref = get_named_key_uref(client, contract_hash, ["lp_balances", "balances", "lp_token_balances"])
        if not balances_uref:
            raise ValueError("Could not find LP balances key")
        dict_key = account_dict_key(client, user)
        result = client.get_dictionary_item(balances_uref, dict_key)
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"public_key": user, "lp_balance": parse_cl_value(cl)}

    if query_type == "amm_stake_info":
        user = kwargs.get("public_key")
        if not user or not validate_public_key(user):
            raise ValueError("public_key required")
        stake_uref = get_named_key_uref(client, contract_hash, ["stake_info", "staking_info", "user_stakes", "stakes"])
        if not stake_uref:
            raise ValueError("Could not find stake info key")
        dict_key = account_dict_key(client, user)
        result = client.get_dictionary_item(stake_uref, dict_key)
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"public_key": user, "stake_info": parse_cl_value(cl)}

    if query_type == "all_proposals":
        count_uref = get_named_key_uref(client, contract_hash, ["proposal_count", "total_proposals", "next_proposal_id"])
        count = "N/A"
        if count_uref:
            r = client.query_global_state(count_uref)
            count = parse_cl_value(r.get("stored_value", {}).get("CLValue"))
        proposals_uref = get_named_key_uref(client, contract_hash, ["proposals", "all_proposals", "proposal_list"])
        return {"proposal_count": count, "proposals_uref": proposals_uref}

    if query_type == "proposal_detail":
        proposal_id = kwargs.get("proposal_id")
        if not proposal_id:
            raise ValueError("proposal_id required")
        proposals_uref = get_named_key_uref(client, contract_hash, ["proposals", "all_proposals", "proposal_list"])
        if not proposals_uref:
            raise ValueError("Could not find proposals key")
        result = client.get_dictionary_item(proposals_uref, str(proposal_id))
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"proposal_id": proposal_id, "proposal": parse_cl_value(cl)}

    if query_type == "vote_record":
        voter = kwargs.get("public_key")
        proposal_id = kwargs.get("proposal_id")
        if not voter or not proposal_id:
            raise ValueError("public_key and proposal_id required")
        votes_uref = get_named_key_uref(client, contract_hash, ["votes", "vote_records", "voter_records"])
        if not votes_uref:
            raise ValueError("Could not find votes key")
        account_hash = account_dict_key(client, voter)
        dict_key = f"{proposal_id}_{account_hash}"
        result = client.get_dictionary_item(votes_uref, dict_key)
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"proposal_id": proposal_id, "voter": voter, "vote": parse_cl_value(cl)}

    if query_type == "asset_record":
        asset_id = kwargs.get("asset_id")
        if not asset_id:
            raise ValueError("asset_id required")
        assets_uref = get_named_key_uref(client, contract_hash, ["assets", "asset_records", "records", "rwa_assets"])
        if not assets_uref:
            raise ValueError("Could not find assets key")
        result = client.get_dictionary_item(assets_uref, str(asset_id))
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"asset_id": asset_id, "record": parse_cl_value(cl)}

    if query_type == "open_orders":
        user = kwargs.get("public_key")
        if not user or not validate_public_key(user):
            raise ValueError("public_key required")
        orders_uref = get_named_key_uref(client, contract_hash, ["user_orders", "orders", "open_orders", "order_book"])
        if not orders_uref:
            raise ValueError("Could not find orders key")
        dict_key = account_dict_key(client, user)
        result = client.get_dictionary_item(orders_uref, dict_key)
        stored = result.get("stored_value", {})
        cl = stored.get("CLValue") or stored.get("cl_value")
        return {"public_key": user, "orders": parse_cl_value(cl)}

    raise ValueError(f"Unknown dapp query_type: {query_type}")


# ---------------------------------------------------------------------------
# Enhanced staking reads
# ---------------------------------------------------------------------------

def staking_read(client: CasperRpcClient, query_type: str, **kwargs) -> dict[str, Any]:
    if query_type == "validator_detail":
        pub_key = kwargs.get("public_key")
        if not pub_key or not validate_public_key(pub_key):
            raise ValueError("validator public_key required")
        result = client.get_auction_info()
        bids = result.get("auction_state", {}).get("bids", [])
        bid = next((b for b in bids if b.get("public_key") == pub_key), None)
        if not bid:
            raise ValueError("Validator not found")
        b = bid.get("bid", {})
        delegators = b.get("delegators", [])
        total_delegated = sum(int(d.get("staked_amount", 0)) for d in delegators)
        return {
            "public_key": pub_key,
            "staked_cspr": motes_to_cspr(b.get("staked_amount", 0)),
            "delegation_rate": b.get("delegation_rate"),
            "inactive": b.get("inactive", False),
            "delegator_count": len(delegators),
            "total_delegated_cspr": motes_to_cspr(total_delegated),
            "top_delegators": [
                {
                    "public_key": d.get("public_key"),
                    "staked_cspr": motes_to_cspr(d.get("staked_amount", 0)),
                }
                for d in sorted(delegators, key=lambda x: int(x.get("staked_amount", 0)), reverse=True)[:5]
            ],
        }

    if query_type == "delegation":
        delegator = kwargs.get("public_key")
        if not delegator or not validate_public_key(delegator):
            raise ValueError("delegator public_key required")
        result = client.get_auction_info()
        bids = result.get("auction_state", {}).get("bids", [])
        delegations = []
        for bid in bids:
            for d in bid.get("bid", {}).get("delegators", []):
                if d.get("delegator_public_key") == delegator or d.get("public_key") == delegator:
                    delegations.append(
                        {
                            "validator": bid.get("public_key"),
                            "staked_cspr": motes_to_cspr(d.get("staked_amount", 0)),
                        }
                    )
        total = sum(int(d.get("staked_amount", 0)) for bid in bids for d in bid.get("bid", {}).get("delegators", []) if d.get("delegator_public_key") == delegator or d.get("public_key") == delegator)
        return {
            "delegator": delegator,
            "delegations": delegations,
            "total_delegated_cspr": motes_to_cspr(total),
        }

    raise ValueError(f"Use casper_staking_info for {query_type}, or unknown query")
