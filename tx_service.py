"""Execute Casper write operations via Node.js tx_runner (casper-js-sdk)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

try:
    from .config import is_signing_configured, load_config
except ImportError:
    from config import is_signing_configured, load_config

_SCRIPT_DIR = Path(__file__).resolve().parent / "scripts"
_TX_RUNNER = _SCRIPT_DIR / "tx_runner.mjs"


class CasperTransactionError(Exception):
    pass


def _node_available() -> bool:
    return shutil.which("node") is not None


def _deps_installed() -> bool:
    return (_SCRIPT_DIR / "node_modules" / "casper-js-sdk").exists()


def run_tx_operation(operation: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_signing_configured():
        raise CasperTransactionError(
            "No signing key configured. Set CASPER_SIGNING_KEY_HEX or CASPER_SIGNING_KEY_PEM."
        )
    if not _node_available():
        raise CasperTransactionError("Node.js is required for write operations. Install Node.js 18+.")
    if not _TX_RUNNER.exists():
        raise CasperTransactionError(f"tx_runner not found at {_TX_RUNNER}")
    if not _deps_installed():
        raise CasperTransactionError(
            "Transaction dependencies missing. Run: cd scripts && npm install"
        )

    cfg = load_config()
    env = os.environ.copy()
    env.setdefault("CASPER_NODE_URL", cfg.node_url)
    env.setdefault("CASPER_CHAIN_NAME", cfg.chain_name)
    if cfg.api_key:
        env.setdefault("CASPER_API_KEY", cfg.api_key)
    if cfg.signing_key_hex:
        env.setdefault("CASPER_SIGNING_KEY_HEX", cfg.signing_key_hex)
    if cfg.signing_key_pem:
        env.setdefault("CASPER_SIGNING_KEY_PEM", cfg.signing_key_pem)

    proc = subprocess.run(
        ["node", str(_TX_RUNNER), operation, json.dumps(params or {})],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=str(_SCRIPT_DIR),
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if not stdout:
        raise CasperTransactionError(stderr or f"tx_runner failed with exit code {proc.returncode}")
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CasperTransactionError(f"Invalid tx_runner output: {stdout[:200]}") from exc
    if "error" in result:
        raise CasperTransactionError(result["error"])
    return result


def transfer_cspr(to_public_key: str, amount_cspr: str | float) -> dict[str, Any]:
    return run_tx_operation(
        "transfer",
        {"to_public_key": to_public_key, "amount_cspr": str(amount_cspr)},
    )
