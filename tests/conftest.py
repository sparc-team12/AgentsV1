import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Keep every test run on the same explicit "today" (REQ-028) and off the real
# state file, so a test can move the materiality threshold without side effects.
os.environ.setdefault("APP_TODAY", "2026-09-18")
os.environ["STATE_DIR"] = tempfile.mkdtemp(prefix="ifa-tests-")
os.environ.pop("TABLE_NAME", None)

import pytest  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        c.post("/api/v1/auth/login", json={
            "email": "kitchen.manager@example.com", "password": "kitchen-demo-2026",
        })
        yield c


@pytest.fixture(autouse=True)
def default_threshold():
    config.set_materiality_threshold_paise(config.DEFAULT_MATERIALITY_THRESHOLD_PAISE)
    yield
    config.set_materiality_threshold_paise(config.DEFAULT_MATERIALITY_THRESHOLD_PAISE)
