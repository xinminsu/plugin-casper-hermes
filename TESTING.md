# Casper Hermes Plugin — Testing Guide

This document describes how to verify the **plugin-casper-hermes** plugin end-to-end: CLI smoke tests, direct Python handler tests, Hermes integration, and optional on-chain write tests.

**Plugin version:** 1.1.0  
**Default network:** Casper testnet (`casper-test`)  
**Public RPC:** `https://node.testnet.casper.network/rpc`

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Setup](#2-environment-setup)
3. [Quick Smoke Test (CLI)](#3-quick-smoke-test-cli)
4. [Python Handler Tests](#4-python-handler-tests)
5. [Hermes Integration Tests](#5-hermes-integration-tests)
6. [Tool Test Matrix](#6-tool-test-matrix)
7. [Write Operation Tests](#7-write-operation-tests)
8. [Alerts Tests](#8-alerts-tests)
9. [Troubleshooting](#9-troubleshooting)
10. [Test Checklist](#10-test-checklist)

---

## 1. Prerequisites

| Component | Required for | Minimum version |
|-----------|--------------|-----------------|
| Python | All read tests, alerts, wallet generation | 3.9+ |
| Node.js | Write operations (`tx_runner.mjs`) | 18+ |
| npm | Installing `casper-js-sdk` in `scripts/` | 9+ |
| pycspr | `casper_generate_wallet` only | 1.2+ |
| Hermes Agent | Integration / natural-language tests | Latest |

**Optional:**

- A funded Casper testnet account (for write tests)
- A known testnet public key, contract hash, or deploy hash (see [Test Fixtures](#test-fixtures))

---

## 2. Environment Setup

### 2.1 Install the plugin

```bash
# Linux / macOS
cp -r plugin-casper-hermes ~/.hermes/plugins/casper

# Windows (PowerShell)
Copy-Item -Recurse plugin-casper-hermes %LOCALAPPDATA%\hermes\plugins\casper
```

Enable in Hermes:

```bash
hermes plugins enable casper
hermes plugins list
```

**Expected:** Plugin appears as `✓ casper v1.1.0 (16 tools)`.

### 2.2 Environment variables

Copy `.env.example` to `~/.hermes/.env` or export in your shell:

```bash
export CASPER_NODE_URL=https://node.testnet.casper.network/rpc
export CASPER_CHAIN_NAME=casper-test
```

For write tests, also set:

```bash
export CASPER_SIGNING_KEY_HEX=<your-ed25519-private-key-hex>
```

### 2.3 Install dependencies

**Read-only tests:** no extra packages required.

**Wallet generation:**

```bash
pip install pycspr
```

**Write operations:**

```bash
cd scripts
npm install
cd ..
```

Verify Node bridge:

```bash
node scripts/tx_runner.mjs
```

**Expected:** JSON error listing available operations (confirms the script runs).

---

## 3. Quick Smoke Test (CLI)

The bundled CLI exercises the RPC layer without Hermes.

From the plugin root:

```bash
python scripts/casper_client.py status
python scripts/casper_client.py block --latest
python scripts/casper_client.py validators
```

### Expected output (status)

```
Chain: casper-test
API version: 2.0.0
Peers: <number > 0>
Last block height: <positive integer>
Last block time: <UTC timestamp>
```

### Expected exit code

`0` on success; non-zero if RPC is unreachable.

---

## 4. Python Handler Tests

Run these from the **plugin root directory** so imports resolve correctly.

### 4.1 Network and gas

```bash
python -c "
import tools
print(tools.casper_network_query({'query_type': 'node_status'}))
print(tools.casper_gas_query({'query_type': 'gas_info'}))
"
```

**Pass criteria:**

- Both lines are valid JSON.
- No `"error"` key in the response.
- `node_status` includes `chainspec_name`, `last_block_height`.
- `gas_info` includes `gas_price` and `standard_transfer_cspr`.

### 4.2 Balance lookup

Replace `<PUBLIC_KEY>` with a known testnet account (68 hex chars, starts with `01`–`03`):

```bash
python -c "
import tools
print(tools.casper_get_balance({'address': '<PUBLIC_KEY>'}))
"
```

**Pass criteria:** JSON with `balance_cspr`, `balance_motes`, `main_purse`.

You can find active accounts on [testnet.cspr.live](https://testnet.cspr.live/).

### 4.3 Staking read

```bash
python -c "
import tools
print(tools.casper_staking_read({'query_type': 'auction_info'}))
print(tools.casper_staking_read({'query_type': 'era_validators'}))
"
```

**Pass criteria:** JSON with `era_id`, validator/bid counts.

### 4.4 Deploy status

Use a recent deploy hash from [testnet.cspr.live](https://testnet.cspr.live/):

```bash
python -c "
import tools
print(tools.casper_deploy_status({'deploy_hash': '<DEPLOY_HASH_64_HEX>'}))
"
```

**Pass criteria:** JSON with `status` of `success`, `failed`, or `pending`.

---

## 5. Hermes Integration Tests

### 5.1 Plugin discovery

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list
```

**Pass criteria:** Log shows `casper` loaded with 16 tools; no traceback during `register()`.

### 5.2 Natural-language prompts

Start Hermes and try these prompts:

| # | Prompt | Expected tool(s) |
|---|--------|------------------|
| 1 | "What is the Casper testnet node status?" | `casper_network_query` |
| 2 | "Get CSPR balance for `<PUBLIC_KEY>`" | `casper_get_balance` |
| 3 | "Show top Casper validators" | `casper_staking_read` or `casper_network_query` |
| 4 | "Look up deploy `<DEPLOY_HASH>`" | `casper_deploy_status` |
| 5 | "What are current Casper gas fees?" | `casper_gas_query` |

### 5.3 Load bundled skill

In a Hermes session:

```
skill_view("casper:casper")
```

**Pass criteria:** Skill content loads without error; lists all 16 tools.

### 5.4 Plugin status command

```
/plugins
```

**Expected:**

```
Plugins (1):
  ✓ casper v1.1.0 (16 tools)
```

---

## 6. Tool Test Matrix

Use this table to track coverage. Each test should return JSON **without** an `"error"` key unless testing invalid input.

### 6.1 Read tools

| Tool | Sample arguments | Pass criteria |
|------|------------------|---------------|
| `casper_get_balance` | `{"address": "<PUBLIC_KEY>"}` | `balance_cspr` present |
| `casper_account_read` | `{"query_type": "account_info", "address": "<PUBLIC_KEY>"}` | `account_hash`, `balance_cspr` |
| `casper_account_read` | `{"query_type": "purse_balance", "uref": "<UREF>"}` | `balance_motes`, `proof` |
| `casper_account_read` | `{"query_type": "contract_info", "contract_hash": "<HASH>"}` | `contract_hash`, `entry_point_count` |
| `casper_account_read` | `{"query_type": "contract_named_keys", "contract_hash": "<HASH>"}` | `named_keys` array |
| `casper_network_query` | `{"query_type": "node_status"}` | `chainspec_name`, `peer_count` |
| `casper_network_query` | `{"query_type": "latest_block"}` | `height`, `hash` |
| `casper_network_query` | `{"query_type": "peers"}` | `peer_count` > 0 |
| `casper_network_query` | `{"query_type": "state_root_hash"}` | `state_root_hash` (64 hex) |
| `casper_network_query` | `{"query_type": "chainspec"}` | chainspec object |
| `casper_gas_query` | `{"query_type": "gas_info"}` | `gas_price`, fee guidance |
| `casper_gas_query` | `{"query_type": "estimate_cost", "payment_motes": "2500000000"}` | RPC estimate object |
| `casper_token_read` | `{"query_type": "total_supply", "contract_hash": "<CEP18_HASH>"}` | `total_supply` |
| `casper_token_read` | `{"query_type": "balance_of", "contract_hash": "<HASH>", "owner": "<PK>"}` | `balance` |
| `casper_token_read` | `{"query_type": "metadata", "contract_hash": "<HASH>"}` | `name`, `symbol`, `decimals` |
| `casper_token_read` | `{"query_type": "nft_owner_of", "contract_hash": "<HASH>", "token_id": "1"}` | `owner` |
| `casper_staking_read` | `{"query_type": "era_validators"}` | `validators` list |
| `casper_staking_read` | `{"query_type": "validator_detail", "public_key": "<VALIDATOR_PK>"}` | stake, delegator info |
| `casper_staking_read` | `{"query_type": "delegation", "public_key": "<DELEGATOR_PK>"}` | `delegations` |
| `casper_staking_read` | `{"query_type": "era_summary"}` | `total_rewards_cspr` |
| `casper_dapp_read` | `{"query_type": "counter_value", "contract_hash": "<HASH>"}` | `count` |
| `casper_dapp_read` | `{"query_type": "amm_reserves", "contract_hash": "<HASH>"}` | reserve fields |
| `casper_deploy_status` | `{"deploy_hash": "<HASH>"}` | `status`, `gas_consumed` |

> **Note:** Token and DApp tests require contracts deployed on testnet with conventional named keys (same conventions as the Eliza `plugin-casper`). Skip or mark N/A if you do not have contract hashes.

### 6.2 Utility tools

| Tool | Sample arguments | Pass criteria |
|------|------------------|---------------|
| `casper_generate_wallet` | `{}` | `public_key`, `private_key_hex`, `account_hash` |
| `casper_alerts` | `{"action": "list"}` | `alerts` array (may be empty) |

---

## 7. Write Operation Tests

> **Warning:** Write tests spend testnet CSPR and are irreversible. Use a dedicated test wallet with minimal funds.

### 7.1 Preconditions

```bash
export CASPER_SIGNING_KEY_HEX=<test-wallet-private-key>
cd scripts && npm install && cd ..
node --version   # must be 18+
```

Fund the corresponding public key via [testnet faucet](https://testnet.cspr.live/) if needed.

### 7.2 Native transfer (smoke)

```bash
python -c "
import tools
print(tools.casper_native_write({
    'operation': 'transfer',
    'to_public_key': '<RECIPIENT_PUBLIC_KEY>',
    'amount_cspr': '0.1'
}))
"
```

**Pass criteria:**

- JSON with `deploy_hash` and `explorer_url`.
- Deploy appears on [testnet.cspr.live](https://testnet.cspr.live/) with status **success**.

Verify with:

```bash
python -c "
import tools
print(tools.casper_deploy_status({'deploy_hash': '<DEPLOY_HASH_FROM_ABOVE>'}))
"
```

### 7.3 Contract write operations

Replace `<CONTRACT_HASH>` and parameters with your deployed contract.

| Tool | operation | Minimal test |
|------|-----------|--------------|
| `casper_native_write` | `create_purse` | `{"operation": "create_purse", "purse_name": "test"}` |
| `casper_token_write` | `transfer` | Requires CEP-18 contract + recipient |
| `casper_nft_write` | `mint` | Requires CEP-47/78 contract |
| `casper_staking_write` | `delegate` | `validator`, `amount_cspr` |
| `casper_defi_write` | `swap` | Requires AMM contract |
| `casper_dapp_write` | `counter_increment` | Requires counter contract |
| `casper_dapp_write` | `call_contract` | `entry_point`, `args` |

Example generic contract call:

```bash
python -c "
import tools
print(tools.casper_dapp_write({
    'operation': 'call_contract',
    'contract_hash': '<CONTRACT_HASH>',
    'entry_point': '<ENTRY_POINT>',
    'args': {'key': 'value'}
}))
"
```

### 7.4 Direct Node bridge test

Bypass Python and test the bridge directly:

```bash
node scripts/tx_runner.mjs transfer '{"to_public_key":"<PK>","amount_cspr":"0.1"}'
```

**Pass criteria:** Single-line JSON with `deploy_hash`, exit code `0`.

---

## 8. Alerts Tests

Alerts are stored at `~/.hermes/casper_alerts.json` (override with `CASPER_ALERTS_FILE`).

```bash
python -c "
import tools
# Add balance alert
print(tools.casper_alerts({
    'action': 'add',
    'alert_type': 'balance',
    'address': '<PUBLIC_KEY>',
    'threshold': 0.001
}))
# List
print(tools.casper_alerts({'action': 'list'}))
# Check (evaluates thresholds)
print(tools.casper_alerts({'action': 'check'}))
# Remove (use id from add response)
print(tools.casper_alerts({'action': 'remove', 'alert_id': '<ALERT_ID>'}))
"
```

**Pass criteria:**

- `add` returns `id`, `type`, `created_at`.
- `list` includes the new alert.
- `check` returns `triggered` array (may be empty if threshold not met).
- `remove` returns the deleted alert object.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Plugin not listed | Not copied or not enabled | `hermes plugins enable casper` |
| `ImportError: attempted relative import` | Wrong working directory | Run CLI/tests from plugin root |
| RPC timeout / connection refused | Network or bad URL | Check `CASPER_NODE_URL` |
| `Account not found` | Invalid address or unfunded account | Verify on testnet.cspr.live |
| Write: `Node.js is required` | Node not installed | Install Node 18+ |
| Write: `Transaction dependencies missing` | npm not run | `cd scripts && npm install` |
| Write: `No signing key configured` | Missing env var | Set `CASPER_SIGNING_KEY_HEX` |
| Token/DApp read: named key not found | Contract uses non-standard keys | Use a compatible contract or adjust named key names |
| `pycspr is required` | Wallet generation without pycspr | `pip install pycspr` |

Debug plugin loading:

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list
hermes logs --level WARNING | grep -i plugin
```

---

## 10. Test Checklist

Copy this checklist when validating a release:

### Read path (no signing key required)

- [ ] `python scripts/casper_client.py status` succeeds
- [ ] `casper_network_query` → `node_status`, `latest_block`, `peers`
- [ ] `casper_get_balance` with known public key
- [ ] `casper_gas_query` → `gas_info`
- [ ] `casper_staking_read` → `auction_info`, `era_validators`
- [ ] `casper_deploy_status` with known deploy hash
- [ ] `casper_alerts` → add, list, check, remove
- [ ] Hermes loads plugin with 16 tools
- [ ] `skill_view("casper:casper")` loads skill

### Write path (testnet wallet + Node.js)

- [ ] `cd scripts && npm install` completes
- [ ] `node scripts/tx_runner.mjs` lists operations
- [ ] `casper_native_write` → `transfer` (small amount)
- [ ] `casper_deploy_status` confirms transfer deploy
- [ ] (Optional) CEP-18 / NFT / staking / DeFi / DApp write on known contracts

### Wallet generation

- [ ] `pip install pycspr`
- [ ] `casper_generate_wallet` returns keypair JSON

---

## Test Fixtures

Replace placeholders when running tests:

| Placeholder | Description | Where to find |
|-------------|-------------|---------------|
| `<PUBLIC_KEY>` | 68-char hex Ed25519 public key | testnet.cspr.live, faucet wallet |
| `<DEPLOY_HASH>` | 64-char deploy hash | Any recent transaction on explorer |
| `<CONTRACT_HASH>` | 64-char contract hash | Your deployed contract |
| `<VALIDATOR_PK>` | Validator public key from auction | `casper_staking_read` → `era_validators` |
| `<UREF>` | Purse URef from account info | `casper_account_read` → `account_info` |

---

## Reporting Issues

When filing a bug report, include:

1. Plugin version (`plugin.yaml` → `1.1.0`)
2. Python version (`python --version`)
3. Node version (`node --version`) for write issues
4. `CASPER_NODE_URL` and `CASPER_CHAIN_NAME` (never include private keys)
5. Exact tool name + JSON arguments
6. Full JSON response or error message
7. Relevant log output (`HERMES_PLUGINS_DEBUG=1`)

---

*Last updated for plugin v1.1.0*
