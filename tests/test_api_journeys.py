"""The PRD's six-step acceptance sequence, driven through the HTTP API.

"A reviewer, working only from the interface, can complete the following
sequence unaided" — PRD Success Metrics. Steps 3 and 5 are the ones the client
says distinguish this from a reorder report, so they get the most scrutiny.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_every_screen_is_unreachable_before_signing_in():
    """REQ-043 / US-030 AC-1."""
    with TestClient(app) as anon:
        for path in ("/api/v1/risks", "/api/v1/setup/status", "/api/v1/chat", "/api/v1/auth/me"):
            method = anon.post if path == "/api/v1/chat" else anon.get
            response = method(path, json={"question": "why"}) if path == "/api/v1/chat" else method(path)
            assert response.status_code == 401, path


def test_each_persona_has_its_own_credentials_and_identical_access():
    """REQ-044 / US-030 AC-4 and AC-5 (OQ-9: no restricted view for fb-manager)."""
    with TestClient(app) as c:
        bad = c.post("/api/v1/auth/login", json={
            "email": "kitchen.manager@example.com", "password": "fandb-demo-2026"})
        assert bad.status_code == 401, "one persona's password must not open the other's account"

    payloads = {}
    for email, password, persona in [
        ("kitchen.manager@example.com", "kitchen-demo-2026", "kitchen-manager"),
        ("fb.manager@example.com", "fandb-demo-2026", "fb-manager"),
    ]:
        with TestClient(app) as c:
            login = c.post("/api/v1/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200
            assert login.json()["user"]["persona"] == persona
            payloads[persona] = c.get("/api/v1/risks").json()
    assert payloads["kitchen-manager"] == payloads["fb-manager"]


def test_step_1_dashboard_lists_risks_by_severity_with_a_total_exposure(client):
    """Acceptance step 1 — REQ-023, REQ-024, REQ-025, REQ-026, REQ-027, REQ-034."""
    body = client.get("/api/v1/risks").json()
    assert body["rows"], "the dashboard is empty"
    assert body["total_waste_exposure"].startswith("Rs ")
    for row in body["rows"]:
        assert row["risk_type"] in {"stockout", "spoilage"}
        assert row["severity"] in {"Critical", "High", "Low"}   # REQ-034, text not colour
        if row["risk_type"] == "stockout":
            assert row["order_by_date"]                          # REQ-025
        else:
            assert row["waste_cost"]                             # REQ-026


def test_step_2_a_flagged_perishable_shows_a_rupee_estimate_and_its_use_by_date(client):
    """Acceptance step 2 — REQ-011, REQ-035."""
    rows = client.get("/api/v1/risks").json()["rows"]
    spoilage = next(r for r in rows if r["risk_type"] == "spoilage")
    detail = client.get(f"/api/v1/risks/{spoilage['ingredient_id']}").json()
    assert detail["spoilage"]["waste_cost"].startswith("Rs ")
    assert detail["spoilage"]["use_by_date"]


def test_step_3_explanation_names_dishes_dates_and_lead_time_and_matches_the_screen(client):
    """Acceptance step 3 — REQ-013 to REQ-016, and REQ-031 consistency.

    The client's framing: a vague or inconsistent answer here fails acceptance
    regardless of how the dashboard looks.
    """
    rows = client.get("/api/v1/risks").json()["rows"]
    stockout = next(r for r in rows if r["risk_type"] == "stockout" and r["order_by_date"])
    detail = client.get(f"/api/v1/risks/{stockout['ingredient_id']}").json()

    answer = client.post("/api/v1/chat", json={
        "question": f"why is {stockout['ingredient_name']} flagged?",
        "ingredient_id": stockout["ingredient_id"],
    }).json()

    assert answer["intent"] == "explain"
    text = answer["answer"]

    # REQ-014 — contributing dishes named
    assert any(c["dish_name"] in text for c in detail["demand"]["contributions"][:3])
    # REQ-015 — the dates driving the flag
    assert detail["stockout"]["projected_stockout_date"] in text
    assert detail["stockout"]["order_by_date"] in text
    # REQ-016 — the supplier lead time that set the order-by date
    assert f"{detail['ingredient']['lead_time_days']} days" in text
    # REQ-031 — the figures quoted match the ones the screen shows
    figures = {f["label"]: f["value"] for f in answer["figures"]}
    assert figures["order-by date"] == detail["stockout"]["order_by_date"]
    assert figures["supplier lead time"] == f"{detail['ingredient']['lead_time_days']} days"
    assert figures["severity"] == detail["stockout"]["severity"]


def test_step_4_order_by_precedes_stockout_by_at_least_the_lead_time(client):
    """Acceptance step 4 — REQ-007."""
    from datetime import date

    rows = client.get("/api/v1/risks").json()["rows"]
    checked = 0
    for row in [r for r in rows if r["risk_type"] == "stockout" and r["order_by_date"]]:
        detail = client.get(f"/api/v1/risks/{row['ingredient_id']}").json()
        so = detail["stockout"]
        gap = (date.fromisoformat(so["projected_stockout_date"])
               - date.fromisoformat(so["order_by_date"])).days
        assert gap >= detail["ingredient"]["lead_time_days"]
        checked += 1
    assert checked > 0


def test_step_5_a_plain_language_menu_change_moves_the_risk_picture(client):
    """Acceptance step 5 — REQ-017 to REQ-020, REQ-036.

    "The risk table updates; at least one ingredient changes state or date."
    """
    dishes = client.get("/api/v1/setup/menu").json()["dishes"]
    dish = next(d for d in dishes if d["name"] == "Chicken Dum Biryani")

    answer = client.post("/api/v1/chat", json={
        "question": f"what if we add a 400-cover banquet of {dish['name']} next Saturday?",
    }).json()

    assert answer["intent"] == "what_if"          # REQ-017, routed off the same endpoint (REQ-036)
    assert "newly_at_risk" in answer              # REQ-018
    assert "order_by_dates_moved" in answer       # REQ-019
    assert "waste_exposure" in answer             # REQ-020
    moved = answer["newly_at_risk"] or answer["order_by_dates_moved"]
    assert moved, "a 400-cover banquet must change at least one ingredient's state or date"
    assert answer["listing"]["rows"], "the scenario-adjusted risk table came back empty"


def test_step_6_purchase_order_draft_names_supplier_item_quantity_and_date(client):
    """Acceptance step 6 — REQ-021, REQ-022."""
    rows = client.get("/api/v1/risks").json()["rows"]
    stockout = next(r for r in rows if r["risk_type"] == "stockout" and r["order_by_date"])
    po = client.post(f"/api/v1/purchase-orders/draft?ingredient_id={stockout['ingredient_id']}").json()

    assert po["supplier_name"] and po["item"] and po["quantity"] and po["required_delivery_date"]
    for fragment in (po["supplier_name"], po["item"], po["quantity"], po["required_delivery_date"]):
        assert fragment in po["body_text"]
    assert "never" not in po["body_text"].lower()   # the draft is the artifact, not a disclaimer
    assert "REQ-022" in po["note"]                  # nothing is sent automatically


def test_chat_agent_says_so_rather_than_guessing_when_it_cannot_parse(client):
    """journeys.md flags this as a PRD gap; REQ-030 forbids inventing a figure."""
    answer = client.post("/api/v1/chat", json={"question": "is the weather nice today"}).json()
    assert answer["intent"] == "unrecognised"
    assert answer["figures"] == []


def test_explanation_never_introduces_a_figure_the_engines_did_not_compute(client):
    """REQ-030 — every number in an answer must exist in the computed figures."""
    import re

    rows = client.get("/api/v1/risks").json()["rows"]
    for row in rows[:5]:
        detail = client.get(f"/api/v1/risks/{row['ingredient_id']}").json()
        answer = client.post("/api/v1/chat", json={
            "question": f"why is {row['ingredient_name']} flagged?",
            "ingredient_id": row["ingredient_id"],
        }).json()
        computed = set(re.findall(r"\d[\d,.]*", str(detail)))
        computed |= {str(detail["demand"]["total"]), "14"}
        for token in re.findall(r"\d[\d,.]*", answer["answer"]):
            assert token in computed or token.rstrip(".,") in computed, (
                f"{row['ingredient_name']}: answer quotes {token}, which no engine computed")


def test_data_setup_hub_reports_every_category(client):
    """REQ-037 / US-024 AC-1."""
    status = client.get("/api/v1/setup/status").json()
    keys = {c["key"] for c in status["categories"]}
    assert keys == {"menu", "ingredients", "stock", "sales-history"}
    assert all(c["loaded"] for c in status["categories"])
    assert status["fully_loaded"] is True


def test_sales_history_covers_twelve_weeks_per_dish(client):
    """REQ-041 / US-028 AC-1."""
    body = client.get("/api/v1/setup/sales-history").json()
    assert body["expected_days"] == 84
    for dish in body["dishes"]:
        assert dish["days"] >= 84, f"{dish['name']} has only {dish['days']} days"
        assert dish["gap"] is None


def test_hidden_attribute_actually_hides():
    """Regression guard.

    The client shows and hides the login panel, the two views and the empty
    state through the `hidden` attribute. The browser's own rule for that is
    `[hidden] { display: none }` at the lowest possible specificity, so any
    class that sets `display` beats it — `.login-shell` is `display: grid`, and
    the result was a full-viewport login panel sitting on top of a dashboard
    that had loaded correctly underneath. Cheap to assert, expensive to
    rediscover.
    """
    from app import config

    css = (config.WEB_DIR / "styles.css").read_text(encoding="utf-8")
    assert "[hidden]" in css and "display: none !important" in css

    html = (config.WEB_DIR / "index.html").read_text(encoding="utf-8")
    assert "<div id=\"login\"" in html and "<div id=\"app\" hidden>" in html


def test_the_page_and_its_assets_are_served(client):
    """The Lambda serves the browser client itself (ADR-015), so a broken path
    here is a blank page in production with a green test suite."""
    assert client.get("/").status_code == 200
    for asset in ("/static/styles.css", "/static/app.js"):
        response = client.get(asset)
        assert response.status_code == 200, asset
        assert response.content, f"{asset} is empty"


def test_threshold_change_takes_effect_without_a_redeploy(client):
    """REQ-012 / US-009 AC-2."""
    before = client.get("/api/v1/risks").json()
    updated = client.put("/api/v1/config/materiality-threshold",
                         json={"materiality_threshold_paise": 10**12}).json()
    assert [r for r in updated["rows"] if r["risk_type"] == "spoilage"] == []
    assert updated["total_waste_exposure_paise"] == before["total_waste_exposure_paise"]
    client.put("/api/v1/config/materiality-threshold", json={"materiality_threshold_paise": 50_000})
