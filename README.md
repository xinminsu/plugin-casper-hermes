# Casper Blockchain Plugin for Hermes

Hermes AI agent plugin for the [Casper Network](https://casper.network/). Enables natural-language queries and operations on Casper accounts, blocks, deploys, validators, contracts, and CSPR transfers.

Ported from the [Eliza Casper plugin](https://github.com/xinminsu/plugin-casper) and aligned with the [Hermes plugin system](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin).

## Features

| Tool | Type | Description |
|------|------|-------------|
| `casper_get_balance` | Read | CSPR balance by public key or account hash |
| `casper_account_info` | Read | Account details, named keys, thresholds |
| `casper_network_query` | Read | Node status, blocks, peers, era, validators |
| `casper_deploy_status` | Read | Deploy/transaction status |
| `casper_staking_info` | Read | Validators, auction, delegations |
| `casper_contract_query` | Read | Contracts, dictionaries, global state |
| `casper_transfer` | Write | Send CSPR (requires signing key + pycspr) |
| `casper_generate_wallet` | Write | Generate Ed25519 keypair (requires pycspr) |

Read operations use Python standard library only. Write operations require `pycspr`.

## Installation

### Option 1: Copy to Hermes plugins directory (recommended)

```bash
# Linux / macOS
cp -r plugin-casper-hermes ~/.hermes/plugins/casper

# Windows (PowerShell)
Copy-Item -Recurse plugin-casper-hermes %LOCALAPPDATA%\hermes\plugins\casper
```

Enable the plugin:

```bash
hermes plugins enable casper
```

Verify:

```bash
hermes plugins list
# Should show: ✓ casper v1.0.0 (8 tools)
```

### Option 2: Project-local plugin

Place the plugin in your project's `.hermes/plugins/casper/` directory. Hermes discovers project plugins automatically.

## Configuration

Copy `.env.example` to `~/.hermes/.env` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CASPER_NODE_URL` | `https://node.testnet.casper.network/rpc` | JSON-RPC endpoint |
| `CASPER_API_KEY` | — | Optional RPC bearer token |
| `CASPER_CHAIN_NAME` | `casper-test` | Chain name for deploys |
| `CASPER_SIGNING_KEY_HEX` | — | Private key for transfers |

For mainnet:

```bash
export CASPER_NODE_URL=https://node.mainnet.casper.network/rpc
export CASPER_CHAIN_NAME=casper
```

### Write operations

```bash
pip install pycspr
export CASPER_SIGNING_KEY_HEX=<your-ed25519-private-key-hex>
```

## Usage Examples

Ask Hermes naturally:

```
What's the Casper testnet node status?
Get balance for account 02a1b2c3d4e5f6...
Look up deploy hash abc123...
Show top Casper validators
Transfer 0.5 CSPR to 03f4e5d6...
Generate a new Casper wallet
```

Load the bundled skill for detailed workflows:

```
skill_view("casper:casper")
```

## CLI Helper

Standalone script for terminal queries (no Hermes required):

```bash
python scripts/casper_client.py status
python scripts/casper_client.py balance <public_key>
python scripts/casper_client.py block --latest
python scripts/casper_client.py deploy <hash>
python scripts/casper_client.py validators
```

## Plugin Structure

```
plugin-casper-hermes/
├── plugin.yaml          # Manifest
├── __init__.py          # register(ctx) wiring
├── schemas.py           # LLM tool schemas
├── tools.py             # Tool handlers
├── rpc.py               # JSON-RPC client (read)
├── transaction.py       # Transfers & wallet (write)
├── config.py            # Environment config
├── utils.py             # Formatting helpers
├── skills/casper/       # Bundled SKILL.md
└── scripts/             # CLI helper
```

## Development

Debug plugin discovery:

```bash
HERMES_PLUGINS_DEBUG=1 hermes plugins list
```

Test RPC client directly:

```bash
python scripts/casper_client.py status
```

## License

MIT

## Related Projects

- [plugin-casper](https://github.com/xinminsu/plugin-casper) — Eliza / Casper agent plugin
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Self-improving AI agent framework
- [Casper Network Docs](https://docs.casper.network/)
