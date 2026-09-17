"""Configuration, and the tiny mutable-state store.

ADR-014: the materiality threshold and forward horizon are *data*, not code —
REQ-012 requires the threshold be adjustable without a redeploy.

Two backends, chosen by environment, so local development needs nothing
installed and the deployed Lambda needs no database server:

  * DynamoDB  when ``TABLE_NAME`` is set (how it runs on AWS)
  * a JSON file in ``STATE_DIR``  otherwise (how it runs on a laptop)
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]      # repository root
PACKAGE = Path(__file__).resolve().parents[1]    # src/ — what gets deployed
DATA_DIR = Path(os.environ.get("DATA_DIR", PACKAGE / "data"))
WEB_DIR = Path(os.environ.get("WEB_DIR", PACKAGE / "web"))
STATE_DIR = Path(os.environ.get("STATE_DIR", os.environ.get("TMPDIR", "/tmp") if os.name != "nt" else ROOT / ".state"))

TABLE_NAME = os.environ.get("TABLE_NAME")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-only-not-a-secret")
SESSION_COOKIE = "ifa_session"

DEFAULT_MATERIALITY_THRESHOLD_PAISE = 50_000   # REQ-012 — ₹500
DEFAULT_HORIZON_DAYS = 14                      # REQ-001 — at least 14 days
TREND_DECAY = "0.85"                           # REQ-003 — weekly recency weight

# REQ-028: "today" is an explicit input, never read from the clock inside an
# engine. Override with APP_TODAY=YYYY-MM-DD to replay a different day.
_APP_TODAY = os.environ.get("APP_TODAY", "2026-09-18")


def today() -> date:
    return date.fromisoformat(_APP_TODAY)


# --- state store -------------------------------------------------------------

_LOCK = threading.Lock()
_DEFAULTS: dict[str, Any] = {
    "materiality_threshold_paise": DEFAULT_MATERIALITY_THRESHOLD_PAISE,
    "horizon_days": DEFAULT_HORIZON_DAYS,
}


class _JsonStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def get(self, key: str) -> Any:
        return self._read().get(key, _DEFAULTS.get(key))

    def put(self, key: str, value: Any) -> None:
        with _LOCK:
            current = self._read()
            current[key] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(current, indent=2), encoding="utf-8")


class _DynamoStore:
    def __init__(self, table_name: str, region: str) -> None:
        import boto3  # imported lazily so local dev needs no AWS SDK

        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def get(self, key: str) -> Any:
        try:
            item = self.table.get_item(Key={"pk": key}).get("Item")
        except Exception:  # a cold table or a throttle must not take the app down
            return _DEFAULTS.get(key)
        if not item:
            return _DEFAULTS.get(key)
        value = item.get("value")
        return int(value) if isinstance(value, float) or hasattr(value, "to_integral_value") else value

    def put(self, key: str, value: Any) -> None:
        self.table.put_item(Item={"pk": key, "value": value})


def _make_store() -> _JsonStore | _DynamoStore:
    if TABLE_NAME:
        return _DynamoStore(TABLE_NAME, AWS_REGION)
    return _JsonStore(Path(STATE_DIR) / "ifa-state.json")


_store: _JsonStore | _DynamoStore | None = None


def store() -> _JsonStore | _DynamoStore:
    global _store
    if _store is None:
        _store = _make_store()
    return _store


def materiality_threshold_paise() -> int:
    return int(store().get("materiality_threshold_paise"))


def set_materiality_threshold_paise(value: int) -> None:
    store().put("materiality_threshold_paise", int(value))


def horizon_days() -> int:
    return int(store().get("horizon_days"))
