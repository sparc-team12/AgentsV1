"""comp-auth — REQ-043, REQ-044.

Per-user login for the two named personas, each with their own credentials
(REQ-044). Identical access once authenticated — there is deliberately no role
column, because OQ-9 resolved to identical access for both personas.

Out of scope by resolved open question: MFA (OQ-6), self-service password
reset (OQ-7), session idle timeout (OQ-8). The session cookie therefore
carries no expiry, which is a client-accepted posture recorded in
architecture.md 12, not an oversight.

The session is a signed cookie, so no session store is needed. Passwords use
PBKDF2-HMAC-SHA256 from the standard library — argon2 would be preferable and
is the architecture's stated choice, but it needs a compiled wheel; this keeps
the deployment a single dependency-light zip. Noted as a deviation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets

from . import config

PBKDF2_ROUNDS = 240_000

# Seeded demo credentials, overridable per deployment.
SEED_USERS = {
    os.environ.get("KITCHEN_MANAGER_EMAIL", "kitchen.manager@example.com"): {
        "persona": "kitchen-manager",
        "name": "Kitchen Manager",
        "password": os.environ.get("KITCHEN_MANAGER_PASSWORD", "kitchen-demo-2026"),
    },
    os.environ.get("FB_MANAGER_EMAIL", "fb.manager@example.com"): {
        "persona": "fb-manager",
        "name": "F&B Manager",
        "password": os.environ.get("FB_MANAGER_PASSWORD", "fandb-demo-2026"),
    },
}


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)


_CREDENTIALS = {
    email: {"salt": hashlib.sha256(email.encode()).digest()[:16], **meta}
    for email, meta in SEED_USERS.items()
}
for _email, _meta in _CREDENTIALS.items():
    _meta["hash"] = _hash(_meta.pop("password"), _meta["salt"])


def authenticate(email: str, password: str) -> dict | None:
    """REQ-044 — each persona's credentials authenticate only that persona."""
    record = _CREDENTIALS.get((email or "").strip().lower())
    if record is None:
        # constant-ish work on an unknown email, so timing does not leak membership
        _hash(password or "", b"\x00" * 16)
        return None
    if not hmac.compare_digest(_hash(password or "", record["salt"]), record["hash"]):
        return None
    return {"email": email.strip().lower(), "persona": record["persona"], "name": record["name"]}


def issue_session(user: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(user, sort_keys=True).encode()).decode()
    signature = hmac.new(config.SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_session(cookie: str | None) -> dict | None:
    if not cookie or "." not in cookie:
        return None
    payload, _, signature = cookie.rpartition(".")
    expected = hmac.new(config.SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(payload.encode()))
    except Exception:
        return None
