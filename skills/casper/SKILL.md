---
name: casper
description: "Full Casper blockchain integration — reads, tokens, NFTs, staking, DeFi, DApps, alerts, and writes."
version: 1.1.0
author: Casper Community
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Casper, CSPR, Blockchain, CEP-18, CEP-47, CEP-78, Staking, DeFi, NFT, Validator]
    category: blockchain
    requires_toolsets: [casper]
---

# Casper Blockchain Skill (Full Feature Set)

## Read Tools

| Tool | Covers |
|------|--------|
| `casper_get_balance` | CSPR balance (public key, account hash, 0x hex) |
| `casper_account_read` | Account info, named keys, purse+proof, contracts, dictionaries, global state |
| `casper_network_query` | Node status, peers, blocks, deploys, era, validators, transfers, chainspec |
| `casper_gas_query` | Gas info and fee estimation |
| `casper_token_read` | CEP-18 (ERC20-like) + CEP-47/78 NFT queries |
| `casper_staking_read` | Validators, delegation, auction, era summary |
| `casper_dapp_read` | Counter, AMM, governance, RWA, DEX orders |
| `casper_deploy_status` | Transaction/deploy lookup |
| `casper_alerts` | Balance/gas/custom alert CRUD + check |

## Write Tools (require `CASPER_SIGNING_KEY_HEX` + Node.js)

| Tool | Covers |
|------|--------|
| `casper_native_write` | Transfer, purse, associated keys, thresholds, named keys |
| `casper_token_write` | CEP-18 mint/burn/transfer/approve/allowance |
| `casper_nft_write` | CEP-47/78 mint/burn/transfer/approve/batch/metadata/admin |
| `casper_staking_write` | Bond, delegate, unbond, undelegate, withdraw, commission |
| `casper_defi_write` | AMM swap, liquidity, LP stake, claim, DEX orders |
| `casper_dapp_write` | Counter, dictionary, governance, RWA, generic contract call |

## Setup

```bash
pip install pycspr          # wallet generation only
cd scripts && npm install   # write operations
export CASPER_SIGNING_KEY_HEX=...
```

Load: `skill_view("casper:casper")`
