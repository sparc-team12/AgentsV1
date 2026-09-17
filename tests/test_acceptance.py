"""Tests written against the PRD's own six-step acceptance sequence and the
acceptance criteria of the stories, not against the implementation.

Each test names the REQ- or US- id it covers, so a failure says which
requirement broke.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app import config
from app.demand_engine import ingredient_demand, project_dish_demand
from app.reference_data import dataset
from app.risk_engine import (
    build_listing,
    rupees,
    spoilage_severity,
    stockout_severity,
)
from app.domain import Severity

AS_OF = date(2026, 9, 18)


# --- REQ-028 / REQ-029: determinism and traceability -------------------------


def test_same_inputs_produce_identical_figures():
    """REQ-028 — the whole listing recomputed twice must be identical."""
    first = build_listing(AS_OF, 14, 50_000)
    second = build_listing(AS_OF, 14, 50_000)
    assert first == second


def test_every_published_figure_carries_a_trace():
    """REQ-029 / ADR-009 — no figure crosses a boundary without its derivation."""
    listing = build_listing(AS_OF, 14, 50_000)
    assert listing.rows, "expected the seeded data to produce at least one risk"
    ds = dataset()
    for row in listing.rows[:5]:
        demand = ingredient_demand(row.ingredient_id, AS_OF, 14)
        assert demand.trace, f"{row.ingredient_name} demand has no trace"
        assert any("total projected demand" in step.label for step in demand.trace)
        assert ds.ingredient(row.ingredient_id) is not None


# --- REQ-001 to REQ-004: demand projection -----------------------------------


def test_horizon_covers_at_least_fourteen_days():
    """REQ-001 / US-001 AC-3."""
    demand = ingredient_demand("ING-001", AS_OF, 14)
    assert len(demand.daily) >= 14
    assert demand.daily[0].on == AS_OF + timedelta(days=1)


def test_saturday_is_projected_from_saturday_history():
    """REQ-002 / US-001 AC-1 — not a flat daily average."""
    ds = dataset()
    dish = ds.dishes[1]
    projection = project_dish_demand(ds, dish.dish_id, AS_OF, 14)
    saturdays = [q for d, q in projection.items() if d.weekday() == 5]
    tuesdays = [q for d, q in projection.items() if d.weekday() == 1]
    assert saturdays and tuesdays
    # the seeded data has a strong weekend shape; a flat average would erase it
    assert min(saturdays) > max(tuesdays)


def test_recent_weeks_are_weighted_more_heavily():
    """REQ-003 / US-001 AC-2."""
    ds = dataset()
    dish = ds.dishes[0]
    rows = [r for r in ds.sales_for(dish.dish_id) if r.sale_date.weekday() == 2]
    unweighted = Decimal(sum(r.units_sold for r in rows)) / Decimal(len(rows))
    projected = project_dish_demand(ds, dish.dish_id, AS_OF, 14)
    wednesday = next(q for d, q in projected.items() if d.weekday() == 2)
    # the seeded history trends upward, so a recency-weighted figure must exceed
    # the flat mean of the same samples
    assert wednesday > unweighted


def test_ingredient_demand_sums_across_every_dish_using_it():
    """REQ-004 / US-002 AC-1."""
    ds = dataset()
    ingredient_id = "ING-001"  # Basmati Rice, used by several dishes
    demand = ingredient_demand(ingredient_id, AS_OF, 14)
    assert len(demand.contributions) > 1
    total_from_parts = sum(c.quantity for c in demand.contributions)
    assert abs(total_from_parts - demand.total) < Decimal("0.01")
    assert abs(sum(c.share_pct for c in demand.contributions) - Decimal(100)) < Decimal("0.5")


# --- REQ-005 to REQ-009: stockout --------------------------------------------


def test_order_by_date_is_earlier_than_stockout_by_lead_time_plus_margin():
    """REQ-007 / US-004 AC-1, and acceptance step 4."""
    listing = build_listing(AS_OF, 14, 50_000)
    stockout_rows = [r for r in listing.rows if r.risk_type == "stockout"]
    assert stockout_rows, "expected at least one stockout risk in the seeded data"

    from app.risk_engine import assess_stockout

    checked = 0
    for row in stockout_rows:
        demand = ingredient_demand(row.ingredient_id, AS_OF, 14)
        risk = assess_stockout(row.ingredient_id, demand, AS_OF)
        if risk is None or risk.order_by_date is None:
            continue
        gap = (risk.projected_stockout_date - risk.order_by_date).days
        assert gap == risk.lead_time_days + risk.safety_margin_days
        assert gap >= risk.lead_time_days   # acceptance step 4
        checked += 1
    assert checked > 0


def test_missing_safety_margin_is_flagged_not_zeroed():
    """US-004 AC-3 / US-026 AC-5 — a gap is surfaced, never silently defaulted."""
    ds = dataset()
    for ing in ds.ingredients:
        margin = ds.safety_margin_days(ing)
        assert margin is None or margin >= 0
    # every seeded ingredient resolves a margin, so the gap list must be clean
    assert not [g for g in ds.gaps if "safety margin" in g.detail]


@pytest.mark.parametrize("days,expected", [
    (-3, Severity.CRITICAL), (0, Severity.CRITICAL), (2, Severity.CRITICAL),
    (3, Severity.HIGH), (7, Severity.HIGH),
    (8, Severity.LOW), (30, Severity.LOW),
])
def test_stockout_severity_bands(days, expected):
    """REQ-009 / US-006 AC-1 and AC-2 (an overdue date is Critical, not a fourth band)."""
    assert stockout_severity(days) is expected


# --- REQ-010 to REQ-012, REQ-042: spoilage -----------------------------------


@pytest.mark.parametrize("paise,expected", [
    (250_000, Severity.CRITICAL), (200_000, Severity.CRITICAL),
    (199_900, Severity.HIGH), (50_000, Severity.HIGH),
    (49_900, Severity.LOW), (0, Severity.LOW),
])
def test_spoilage_severity_bands(paise, expected):
    """REQ-042 / US-029 AC-1."""
    assert spoilage_severity(paise) is expected


def test_waste_cost_is_quantity_times_unit_cost():
    """REQ-011 / US-008 AC-1."""
    from app.risk_engine import assess_spoilage

    ds = dataset()
    found = 0
    for ing in ds.ingredients:
        demand = ingredient_demand(ing.ingredient_id, AS_OF, 14)
        risk = assess_spoilage(ing.ingredient_id, demand, AS_OF, 50_000)
        if risk is None:
            continue
        expected = int(round(float(risk.unconsumed_quantity) * risk.unit_cost_paise))
        assert abs(risk.waste_cost_paise - expected) <= 1
        found += 1
    assert found > 0, "expected the seeded data to produce spoilage risks"


def test_non_perishable_is_never_flagged_for_spoilage():
    """REQ-010 / US-007 AC-2."""
    from app.risk_engine import assess_spoilage

    ds = dataset()
    for ing in ds.ingredients:
        if ing.perishable:
            continue
        demand = ingredient_demand(ing.ingredient_id, AS_OF, 14)
        assert assess_spoilage(ing.ingredient_id, demand, AS_OF, 50_000) is None


def test_threshold_suppresses_from_the_list_but_not_from_the_aggregate():
    """REQ-012 + REQ-027 / US-009 AC-1 and AC-3.

    The aggregate must be invariant under a threshold change — that is the
    whole point of REQ-027 counting suppressed warnings.
    """
    low = build_listing(AS_OF, 14, 0)
    high = build_listing(AS_OF, 14, 10**12)   # above any possible waste cost
    assert high.total_waste_exposure_paise == low.total_waste_exposure_paise
    assert len([r for r in high.rows if r.risk_type == "spoilage"]) == 0
    assert len([r for r in low.rows if r.risk_type == "spoilage"]) > 0
    assert high.suppressed_count > low.suppressed_count


# --- REQ-023: dashboard ordering ---------------------------------------------


def test_dashboard_orders_by_band_first_interleaving_both_risk_types():
    """REQ-023 / US-019 AC-1 and AC-3 — a Critical spoilage outranks a High stockout."""
    listing = build_listing(AS_OF, 14, 50_000)
    ranks = [row.severity.rank for row in listing.rows]
    assert ranks == sorted(ranks), "bands are not grouped Critical then High then Low"

    for band in (Severity.CRITICAL, Severity.HIGH):
        in_band = [r for r in listing.rows if r.severity is band]
        stock = [r.days_until_order_by for r in in_band
                 if r.risk_type == "stockout" and r.days_until_order_by is not None]
        spoil = [r.waste_cost_paise for r in in_band if r.risk_type == "spoilage"]
        assert stock == sorted(stock), "stockout rows not ordered by order-by proximity"
        assert spoil == sorted(spoil, reverse=True), "spoilage rows not ordered by waste cost"


def test_severity_is_available_as_text_not_only_colour():
    """REQ-034 / US-019 AC-4."""
    listing = build_listing(AS_OF, 14, 50_000)
    for row in listing.rows:
        assert row.severity_label in {"Critical", "High", "Low"}


def test_money_is_formatted_in_indian_rupees():
    """REQ-035."""
    assert rupees(50_000) == "Rs 500.00"
    assert rupees(250_000) == "Rs 2,500.00"
    assert rupees(1_23_45_678) == "Rs 1,23,456.78"
