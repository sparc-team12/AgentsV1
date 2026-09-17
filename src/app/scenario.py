"""comp-scenario — REQ-017 to REQ-020.

A what-if scenario is a pure overlay on top of the immutable baseline, re-run
through the same engines and diffed (ADR-011). Nothing is written anywhere:
the PRD's Non-Goals exclude saving, naming or comparing scenarios, so leaving
a scenario costs nothing and the baseline is never disturbed.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from . import config
from .risk_engine import build_listing, rupees

ZERO = Decimal("0")


def build_overlay(dish_id: str, extra_servings: Decimal, date_from: date,
                  date_to: date) -> dict[str, dict[date, Decimal]]:
    """Spread the additional covers evenly across the named date range."""
    days = max(1, (date_to - date_from).days + 1)
    per_day = Decimal(extra_servings) / Decimal(days)
    span = {date_from + timedelta(days=i): per_day for i in range(days)}
    return {dish_id: span}


def preview(dish_id: str, dish_name: str, extra_servings: Decimal, date_from: date,
            date_to: date, as_of: date | None = None) -> dict[str, Any]:
    """Recompute under the overlay and report what moved.

    REQ-018 newly at-risk ingredients, REQ-019 order-by dates that move,
    REQ-020 the change in total waste exposure.
    """
    as_of = as_of or config.today()
    horizon = config.horizon_days()
    threshold = config.materiality_threshold_paise()

    base = build_listing(as_of, horizon, threshold)
    overlay = build_overlay(dish_id, extra_servings, date_from, date_to)
    after = build_listing(as_of, horizon, threshold, overlay=overlay)

    base_rows = {(r.ingredient_id, r.risk_type): r for r in base.rows}
    after_rows = {(r.ingredient_id, r.risk_type): r for r in after.rows}

    newly_at_risk = [
        {"ingredient_id": key[0], "ingredient_name": row.ingredient_name,
         "risk_type": row.risk_type, "severity": row.severity_label,
         "order_by_date": row.order_by_date.isoformat() if row.order_by_date else None,
         "waste_cost": rupees(row.waste_cost_paise) if row.waste_cost_paise else None}
        for key, row in sorted(after_rows.items()) if key not in base_rows
    ]

    no_longer_at_risk = [
        {"ingredient_id": key[0], "ingredient_name": row.ingredient_name, "risk_type": row.risk_type}
        for key, row in sorted(base_rows.items()) if key not in after_rows
    ]

    moved_dates = []
    for key, row in sorted(after_rows.items()):
        if key[1] != "stockout" or key not in base_rows:
            continue
        before = base_rows[key].order_by_date
        now = row.order_by_date
        if before and now and before != now:
            moved_dates.append({
                "ingredient_id": key[0],
                "ingredient_name": row.ingredient_name,
                "was": before.isoformat(),
                "now": now.isoformat(),
                "days_moved": (now - before).days,
                "direction": "earlier" if now < before else "later",
            })

    delta = after.total_waste_exposure_paise - base.total_waste_exposure_paise
    return {
        "scenario": {
            "dish_id": dish_id,
            "dish_name": dish_name,
            "extra_servings": str(extra_servings),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
        "newly_at_risk": newly_at_risk,
        "no_longer_at_risk": no_longer_at_risk,
        "order_by_dates_moved": moved_dates,
        "waste_exposure": {
            "before_paise": base.total_waste_exposure_paise,
            "after_paise": after.total_waste_exposure_paise,
            "delta_paise": delta,
            "before": rupees(base.total_waste_exposure_paise),
            "after": rupees(after.total_waste_exposure_paise),
            "delta": rupees(delta),
            "direction": "increases" if delta > 0 else ("decreases" if delta < 0 else "is unchanged"),
        },
        "listing": after,   # the scenario-adjusted view, transient (ADR-011)
    }
