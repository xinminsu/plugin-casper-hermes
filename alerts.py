"""Balance and gas alert management for Casper Hermes plugin."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from rpc import CasperRpcClient
from reads import query_gas
from utils import motes_to_cspr, validate_address

DEFAULT_ALERTS_PATH = Path(os.environ.get("CASPER_ALERTS_FILE", Path.home() / ".hermes" / "casper_alerts.json"))


def _load_alerts() -> dict[str, dict[str, Any]]:
    if not DEFAULT_ALERTS_PATH.exists():
        return {}
    try:
        return json.loads(DEFAULT_ALERTS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_alerts(alerts: dict[str, dict[str, Any]]) -> None:
    DEFAULT_ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ALERTS_PATH.write_text(json.dumps(alerts, indent=2), encoding="utf-8")


def add_alert(
    alert_type: str,
    address: str | None = None,
    threshold: float | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    alerts = _load_alerts()
    alert_id = f"alert_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    alert = {
        "id": alert_id,
        "type": alert_type,
        "address": address,
        "threshold": threshold,
        "message": message,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "triggered": False,
    }
    alerts[alert_id] = alert
    _save_alerts(alerts)
    return alert


def list_alerts() -> list[dict[str, Any]]:
    return list(_load_alerts().values())


def remove_alert(alert_id: str) -> dict[str, Any]:
    alerts = _load_alerts()
    if alert_id not in alerts:
        raise ValueError(f"Alert not found: {alert_id}")
    removed = alerts.pop(alert_id)
    _save_alerts(alerts)
    return removed


def check_alerts(client: CasperRpcClient | None = None) -> list[dict[str, Any]]:
    """Evaluate all alerts and return triggered ones."""
    client = client or CasperRpcClient()
    alerts = _load_alerts()
    triggered: list[dict[str, Any]] = []

    for alert_id, alert in alerts.items():
        try:
            if alert.get("type") == "balance":
                address = alert.get("address")
                threshold = alert.get("threshold")
                if not address or threshold is None:
                    continue
                balance = float(client.get_cspr_balance(address)["balance_cspr"])
                if balance >= float(threshold):
                    triggered.append(
                        {
                            **alert,
                            "current_balance_cspr": balance,
                            "notification": f"Balance alert: {address} has {balance} CSPR (threshold: {threshold})",
                        }
                    )
            elif alert.get("type") == "gas":
                threshold = alert.get("threshold")
                gas_info = query_gas(client)
                gas_price = float(gas_info.get("gas_price", 1))
                if threshold is not None and gas_price >= float(threshold):
                    triggered.append(
                        {
                            **alert,
                            "current_gas_price": gas_price,
                            "notification": f"Gas alert: price {gas_price} >= threshold {threshold}",
                        }
                    )
            elif alert.get("type") == "custom" and alert.get("message"):
                triggered.append({**alert, "notification": alert["message"]})
        except Exception as exc:
            triggered.append({**alert, "error": str(exc)})

    return triggered
