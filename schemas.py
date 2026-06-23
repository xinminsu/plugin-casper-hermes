"""Tool schemas for the Casper Hermes plugin."""

NETWORK_PARAM = {
    "network": {
        "type": "string",
        "enum": ["testnet", "mainnet", "casper-test", "casper"],
        "description": (
            "Casper network to query. testnet/casper-test = public testnet; "
            "mainnet/casper = mainnet. Defaults to CASPER_CHAIN_NAME env or testnet."
        ),
    }
}

# --- Read tools ---

CASPER_GET_BALANCE = {
    "name": "casper_get_balance",
    "description": (
        "Get CSPR balance for a Casper wallet. Supports 68-char public key, "
        "64-char account hash, account-hash- prefix, or 0x-prefixed hex (Ethereum-style). "
        "Always specify network (testnet/mainnet) when the chain is ambiguous."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "address": {"type": "string", "description": "Casper public key, account hash, or 0x hex"},
            **NETWORK_PARAM,
        },
        "required": ["address"],
    },
}

CASPER_ACCOUNT_READ = {
    "name": "casper_account_read",
    "description": (
        "Query Casper accounts, purses, contracts, dictionaries, and global state. "
        "Operations: account_info, named_keys, purse_balance (with proof), contract_info, "
        "contract_named_keys, entry_points, dictionary_item, dictionary_by_account, "
        "dictionary_by_contract, global_state, state_item."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": [
                    "account_info", "named_keys", "purse_balance", "contract_info",
                    "contract_named_keys", "entry_points", "dictionary_item",
                    "dictionary_by_account", "dictionary_by_contract", "global_state", "state_item",
                ],
            },
            "address": {"type": "string"},
            "public_key": {"type": "string"},
            "contract_hash": {"type": "string"},
            "named_key": {"type": "string"},
            "dictionary_key": {"type": "string"},
            "uref": {"type": "string"},
            "key": {"type": "string"},
            "path": {"type": "array", "items": {"type": "string"}},
            **NETWORK_PARAM,
        },
        "required": ["query_type"],
    },
}

CASPER_NETWORK_QUERY = {
    "name": "casper_network_query",
    "description": (
        "Query Casper network: node_status, peers, latest_block, block_by_height, block_by_hash, "
        "era_summary, validators, transfers, state_root_hash, chainspec. "
        "Specify network=testnet or mainnet when querying a particular chain."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": [
                    "node_status", "peers", "latest_block", "block_by_height", "block_by_hash",
                    "era_summary", "validators", "transfers", "state_root_hash", "chainspec",
                ],
            },
            "block_height": {"type": "integer"},
            "block_hash": {"type": "string"},
            **NETWORK_PARAM,
        },
        "required": ["query_type"],
    },
}

CASPER_GAS_QUERY = {
    "name": "casper_gas_query",
    "description": "Query Casper gas price guidance and estimate transaction fees.",
    "parameters": {
        "type": "object",
        "properties": {
            "query_type": {"type": "string", "enum": ["gas_info", "estimate_cost"], "default": "gas_info"},
            "payment_motes": {"type": "string", "description": "Payment amount in motes for estimate_cost"},
            "is_module_bytes": {"type": "boolean", "description": "True for contract deploy estimate"},
        },
    },
}

CASPER_TOKEN_READ = {
    "name": "casper_token_read",
    "description": (
        "Query CEP-18 fungible tokens (ERC20-like) and CEP-47/78 NFTs: total_supply, balance_of, "
        "allowance, metadata, nft_owner_of, nft_tokens_of, nft_metadata, nft_approved, "
        "nft_max_supply, nft_batch_owners."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": [
                    "total_supply", "balance_of", "allowance", "metadata",
                    "nft_total_supply", "nft_owner_of", "nft_tokens_of", "nft_metadata",
                    "nft_approved", "nft_max_supply", "nft_batch_owners",
                ],
            },
            "contract_hash": {"type": "string"},
            "owner": {"type": "string"},
            "spender": {"type": "string"},
            "token_id": {"type": "string"},
            "token_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["query_type", "contract_hash"],
    },
}

CASPER_STAKING_READ = {
    "name": "casper_staking_read",
    "description": (
        "Query Casper staking: era_validators, validator_detail, delegation, auction_info, "
        "validator_changes, era_summary."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": ["era_validators", "validator_detail", "delegation", "auction_info", "validator_changes", "era_summary"],
            },
            "public_key": {"type": "string"},
        },
        "required": ["query_type"],
    },
}

CASPER_DAPP_READ = {
    "name": "casper_dapp_read",
    "description": (
        "Query Casper DApps: counter_value, amm_reserves, amm_lp_balance, amm_stake_info, "
        "all_proposals, proposal_detail, vote_record, asset_record, open_orders."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": [
                    "counter_value", "amm_reserves", "amm_lp_balance", "amm_stake_info",
                    "all_proposals", "proposal_detail", "vote_record", "asset_record", "open_orders",
                ],
            },
            "contract_hash": {"type": "string"},
            "public_key": {"type": "string"},
            "proposal_id": {"type": "string"},
            "asset_id": {"type": "string"},
        },
        "required": ["query_type", "contract_hash"],
    },
}

CASPER_DEPLOY_STATUS = {
    "name": "casper_deploy_status",
    "description": (
        "Look up Casper deploy/transaction by hash. query_type: status (summary), deploy (parsed), "
        "raw (full RPC payload), read_fee (gas/fee from execution or payment). "
        "Specify network=testnet or mainnet when the deploy chain is unknown."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "deploy_hash": {"type": "string"},
            "query_type": {
                "type": "string",
                "enum": ["status", "deploy", "raw", "read_fee"],
                "default": "status",
            },
            "finalized_approvals_only": {
                "type": "boolean",
                "description": "Use finalized approvals only (faster, default true)",
                "default": True,
            },
            **NETWORK_PARAM,
        },
        "required": ["deploy_hash"],
    },
}

CASPER_ALERTS = {
    "name": "casper_alerts",
    "description": "Manage Casper alerts: add, list, remove, check (balance/gas/custom monitoring).",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list", "remove", "check"]},
            "alert_type": {"type": "string", "enum": ["balance", "gas", "custom"]},
            "alert_id": {"type": "string"},
            "address": {"type": "string"},
            "threshold": {"type": "number"},
            "message": {"type": "string"},
        },
        "required": ["action"],
    },
}

CASPER_GENERATE_WALLET = {
    "name": "casper_generate_wallet",
    "description": "Generate a new Casper Ed25519 wallet keypair.",
    "parameters": {"type": "object", "properties": {}},
}

# --- Write tools ---

CASPER_NATIVE_WRITE = {
    "name": "casper_native_write",
    "description": (
        "Native CSPR write ops (requires signing key + Node.js): transfer, create_purse, "
        "add_associated_key, remove_associated_key, set_action_threshold, put_named_key."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["transfer", "create_purse", "add_associated_key", "remove_associated_key", "set_action_threshold", "put_named_key"],
            },
            "to_public_key": {"type": "string"},
            "amount_cspr": {"type": "string"},
            "public_key": {"type": "string"},
            "weight": {"type": "integer"},
            "action_type": {"type": "string", "enum": ["deployment", "key_management"]},
            "threshold": {"type": "integer"},
            "name": {"type": "string"},
            "key_value": {"type": "string"},
            "purse_name": {"type": "string"},
        },
        "required": ["operation"],
    },
}

CASPER_TOKEN_WRITE = {
    "name": "casper_token_write",
    "description": "CEP-18 token writes: mint, burn, transfer, approve, increase_allowance, decrease_allowance, transfer_from.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["mint", "burn", "transfer", "approve", "increase_allowance", "decrease_allowance", "transfer_from"],
            },
            "contract_hash": {"type": "string"},
            "owner": {"type": "string"},
            "recipient": {"type": "string"},
            "spender": {"type": "string"},
            "amount": {"type": "string"},
            "decimals": {"type": "integer", "default": 9},
        },
        "required": ["operation", "contract_hash"],
    },
}

CASPER_NFT_WRITE = {
    "name": "casper_nft_write",
    "description": "CEP-47/78 NFT writes: mint, mint_copies, burn, transfer, approve, transfer_from, set_metadata, batch_transfer, batch_burn, set_admin.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["mint", "mint_copies", "burn", "transfer", "approve", "transfer_from", "set_metadata", "batch_transfer", "batch_burn", "set_admin"],
            },
            "contract_hash": {"type": "string"},
            "recipient": {"type": "string"},
            "owner": {"type": "string"},
            "spender": {"type": "string"},
            "admin": {"type": "string"},
            "token_id": {"type": "string"},
            "token_ids": {"type": "array", "items": {"type": "string"}},
            "count": {"type": "integer"},
            "metadata": {"type": "string"},
        },
        "required": ["operation", "contract_hash"],
    },
}

CASPER_STAKING_WRITE = {
    "name": "casper_staking_write",
    "description": "Staking writes: bond, delegate, unbond, undelegate, withdraw_rewards, set_commission_rate.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["bond", "delegate", "unbond", "undelegate", "withdraw_rewards", "set_commission_rate"],
            },
            "validator": {"type": "string"},
            "amount_cspr": {"type": "string"},
            "delegator_rate": {"type": "integer"},
            "commission_rate": {"type": "integer"},
        },
        "required": ["operation"],
    },
}

CASPER_DEFI_WRITE = {
    "name": "casper_defi_write",
    "description": "DeFi AMM/DEX writes: swap, add_liquidity, remove_liquidity, stake_lp, claim_reward, create_order, cancel_order.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["swap", "add_liquidity", "remove_liquidity", "stake_lp", "claim_reward", "create_order", "cancel_order"],
            },
            "contract_hash": {"type": "string"},
            "token_in": {"type": "string"},
            "token_out": {"type": "string"},
            "token_a": {"type": "string"},
            "token_b": {"type": "string"},
            "lp_token": {"type": "string"},
            "amount_in": {"type": "string"},
            "min_amount_out": {"type": "string"},
            "amount_a": {"type": "string"},
            "amount_b": {"type": "string"},
            "lp_amount": {"type": "string"},
            "min_amount_a": {"type": "string"},
            "min_amount_b": {"type": "string"},
            "amount": {"type": "string"},
            "price": {"type": "string"},
            "order_id": {"type": "string"},
            "decimals": {"type": "integer"},
        },
        "required": ["operation", "contract_hash"],
    },
}

CASPER_DAPP_WRITE = {
    "name": "casper_dapp_write",
    "description": (
        "General DApp writes: counter_increment, counter_decrement, dictionary_put, dictionary_remove, "
        "create_proposal, cast_vote, execute_proposal, save_asset_record, call_contract."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "counter_increment", "counter_decrement", "dictionary_put", "dictionary_remove",
                    "create_proposal", "cast_vote", "execute_proposal", "save_asset_record", "call_contract",
                ],
            },
            "contract_hash": {"type": "string"},
            "entry_point": {"type": "string"},
            "args": {"type": "object"},
            "key": {"type": "string"},
            "value": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "voting_duration": {"type": "integer"},
            "proposal_id": {"type": "string"},
            "vote_option": {"type": "string"},
            "asset_id": {"type": "string"},
            "owner_hash": {"type": "string"},
            "document_hash": {"type": "string"},
            "metadata": {"type": "string"},
        },
        "required": ["operation", "contract_hash"],
    },
}
