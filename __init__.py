"""Casper blockchain plugin for Hermes AI agent framework."""

from __future__ import annotations

import logging
from pathlib import Path

try:
    from . import schemas, tools
except ImportError:
    import schemas
    import tools

logger = logging.getLogger(__name__)

TOOLSET = "casper"

_TOOLS = [
    ("casper_get_balance", schemas.CASPER_GET_BALANCE, tools.casper_get_balance),
    ("casper_account_read", schemas.CASPER_ACCOUNT_READ, tools.casper_account_read),
    ("casper_network_query", schemas.CASPER_NETWORK_QUERY, tools.casper_network_query),
    ("casper_gas_query", schemas.CASPER_GAS_QUERY, tools.casper_gas_query),
    ("casper_token_read", schemas.CASPER_TOKEN_READ, tools.casper_token_read),
    ("casper_staking_read", schemas.CASPER_STAKING_READ, tools.casper_staking_read),
    ("casper_dapp_read", schemas.CASPER_DAPP_READ, tools.casper_dapp_read),
    ("casper_deploy_status", schemas.CASPER_DEPLOY_STATUS, tools.casper_deploy_status),
    ("casper_alerts", schemas.CASPER_ALERTS, tools.casper_alerts),
    ("casper_generate_wallet", schemas.CASPER_GENERATE_WALLET, tools.casper_generate_wallet),
    ("casper_native_write", schemas.CASPER_NATIVE_WRITE, tools.casper_native_write),
    ("casper_token_write", schemas.CASPER_TOKEN_WRITE, tools.casper_token_write),
    ("casper_nft_write", schemas.CASPER_NFT_WRITE, tools.casper_nft_write),
    ("casper_staking_write", schemas.CASPER_STAKING_WRITE, tools.casper_staking_write),
    ("casper_defi_write", schemas.CASPER_DEFI_WRITE, tools.casper_defi_write),
    ("casper_dapp_write", schemas.CASPER_DAPP_WRITE, tools.casper_dapp_write),
]


def register(ctx) -> None:
    for name, schema, handler in _TOOLS:
        ctx.register_tool(name=name, toolset=TOOLSET, schema=schema, handler=handler)

    skills_dir = Path(__file__).parent / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                ctx.register_skill(child.name, skill_md)

    logger.info("Casper plugin registered (%d tools)", len(_TOOLS))
