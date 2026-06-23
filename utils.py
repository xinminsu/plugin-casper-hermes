"""Shared formatting and validation helpers."""

from __future__ import annotations

import json
from typing import Any


def truncate(value: str | None, max_len: int = 50) -> str:
    if not value:
        return "N/A"
    return value if len(value) <= max_len else value[:max_len] + "..."


def format_timestamp(ts: int | float | str | None) -> str:
    if ts is None:
        return "N/A"
    from datetime import datetime, timezone

    if isinstance(ts, str):
        normalized = ts.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.strftime("%Y-%m-%d %H:%M:%S UTC")
        except ValueError:
            ts = float(ts)

    value = float(ts)
    seconds = value / 1000 if value > 1_000_000_000_000 else value
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def motes_to_cspr(motes: str | int) -> str:
    try:
        value = int(motes)
    except (TypeError, ValueError):
        return "0"
    whole = value // 1_000_000_000
    frac = value % 1_000_000_000
    if frac == 0:
        return str(whole)
    return f"{whole}.{str(frac).zfill(9).rstrip('0')}"


def cspr_to_motes(amount: str | float) -> int:
    text = str(amount).strip()
    if "." in text:
        whole, frac = text.split(".", 1)
        frac = (frac + "000000000")[:9]
        return int(whole) * 1_000_000_000 + int(frac)
    return int(text) * 1_000_000_000


def validate_public_key(key: str) -> bool:
    return bool(key and len(key) == 68 and all(c in "0123456789abcdefABCDEF" for c in key))


def validate_account_hash(value: str) -> bool:
    clean = value.lower().replace("account-hash-", "")
    return bool(clean and len(clean) == 64 and all(c in "0123456789abcdef" for c in clean))


def normalize_address(address: str) -> str:
    """Normalize Casper address formats including 0x-prefixed account hashes."""
    text = address.strip()
    if text.lower().startswith("account-hash-"):
        return text.lower().replace("account-hash-", "")
    if text.startswith("0x") or text.startswith("0X"):
        hex_part = text[2:]
        if len(hex_part) == 64:
            return hex_part.lower()
        if len(hex_part) == 68:
            return hex_part.lower()
    return text


def validate_address(address: str) -> bool:
    clean = normalize_address(address)
    return validate_public_key(clean) or validate_account_hash(clean)


def resolve_address_input(address: str) -> tuple[str, str]:
    """Return (kind, normalized) where kind is public_key or account_hash."""
    clean = normalize_address(address)
    if validate_public_key(clean):
        return "public_key", clean
    if validate_account_hash(clean):
        return "account_hash", clean
    raise ValueError("Invalid address format")


def validate_contract_hash(value: str) -> bool:
    clean = value.lower().replace("hash-", "").replace("0x", "")
    return bool(clean and len(clean) == 64 and all(c in "0123456789abcdef" for c in clean))


def normalize_contract_hash(value: str) -> str:
    clean = value.lower().replace("hash-", "").replace("0x", "")
    return f"hash-{clean}"


def parse_cl_value(cl_value: dict[str, Any] | None) -> str:
    if not cl_value:
        return "N/A"
    if "parsed" in cl_value:
        parsed = cl_value["parsed"]
        return parsed if isinstance(parsed, str) else json.dumps(parsed)
    if "bytes" in cl_value and "cl_type" in cl_value:
        return f"{cl_value['cl_type']} (raw: {truncate(str(cl_value['bytes']), 40)})"
    return json.dumps(cl_value)
