"""comp-risk-engine — REQ-005 to REQ-012, REQ-023 to REQ-027, REQ-042.

Stockout and spoilage live in one module because the PRD Glossary defines a
single shared Severity scale across both, and REQ-023 requires them
*interleaved* in one ranked list. Splitting them would leave the cross-type
ranking rule in neither module (see architecture.md 4.1).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from . import config
from .demand_engine import all_ingredient_demand
from .domain import (
    IngredientDemand,
    RiskListing,
    RiskRow,
    Severity,
    SpoilageRisk,
    StockoutRisk,
    TraceStep,
)
from .reference_data import dataset

ZERO = Decimal("0")

SPOILAGE_CRITICAL_PAISE = 200_000   # REQ-042 — >= Rs 2000
SPOILAGE_HIGH_PAISE = 50_000        # REQ-042 — Rs 500 - 1999


def stockout_severity(days_until_order_by: int) -> Severity:
    """REQ-009. An order-by date already past falls under '<= 2 days' and is
    Critical — there is deliberately no separate overdue band (US-006 AC-2)."""
    if days_until_order_by <= 2:
        return Severity.CRITICAL
    if days_until_order_by <= 7:
        return Severity.HIGH
    return Severity.LOW


def spoilage_severity(waste_cost_paise: int) -> Severity:
    """REQ-042."""
    if waste_cost_paise >= SPOILAGE_CRITICAL_PAISE:
        return Severity.CRITICAL
    if waste_cost_paise >= SPOILAGE_HIGH_PAISE:
        return Severity.HIGH
    return Severity.LOW


def assess_stockout(ingredient_id: str, demand: IngredientDemand, as_of: date) -> StockoutRisk | None:
    """REQ-005 to REQ-009."""
    ds = dataset()
    ing = ds.ingredient(ingredient_id)
    stock = ds.stock_for(ingredient_id)
    if ing is None or stock is None:
        return None

    on_hand = stock.quantity
    running = ZERO
    stockout_date: date | None = None
    for day in demand.daily:
        running += day.quantity
        if running > on_hand:
            stockout_date = day.on
            break
    if stockout_date is None:
        return None  # REQ-005 — consumption never exhausts stock inside the horizon

    supplier = ds.supplier(ing.supplier_id)
    lead_time = supplier.lead_time_days if supplier else None
    margin = ds.safety_margin_days(ing)

    order_by: date | None = None
    days_until: int | None = None
    suggested: Decimal | None = None
    gap: str | None = None

    if lead_time is None:
        gap = "no supplier mapped, so no lead time — order-by date not computed"
    elif margin is None:
        gap = "no safety margin configured on the ingredient or its supplier — order-by date not computed"
    else:
        # REQ-007 — order-by = stockout date - lead time - safety margin
        order_by = stockout_date - timedelta(days=lead_time + margin)
        days_until = (order_by - as_of).days
        # REQ-008 — cover projected consumption across the lead-time gap
        window_end = stockout_date + timedelta(days=lead_time + margin)
        suggested = sum(
            (d.quantity for d in demand.daily if stockout_date <= d.on <= window_end), ZERO
        ).quantize(Decimal("0.001"))

    severity = stockout_severity(days_until) if days_until is not None else Severity.CRITICAL

    trace = [
        TraceStep(label="quantity on hand", value=f"{on_hand} {ing.unit}", source="current stock"),
        TraceStep(label="projected consumption", value=f"{demand.total} {ing.unit} over the horizon",
                  source="demand projection (REQ-004)"),
        TraceStep(label="projected stockout date", value=stockout_date.isoformat(),
                  source="first day cumulative demand exceeds stock on hand (REQ-006)"),
    ]
    if lead_time is not None:
        trace.append(TraceStep(label="supplier lead time", value=f"{lead_time} days",
                               source=f"supplier {supplier.name}" if supplier else "supplier"))
    if margin is not None:
        trace.append(TraceStep(label="safety margin", value=f"{margin} days",
                               source="configured per ingredient or supplier (REQ-039)"))
    if order_by is not None:
        trace.append(TraceStep(
            label="order-by date", value=order_by.isoformat(),
            source=f"{stockout_date.isoformat()} - {lead_time}d lead time - {margin}d safety margin (REQ-007)"))
        trace.append(TraceStep(label="severity", value=severity.value,
                               source=f"order-by is {days_until} days away (REQ-009)"))
    if suggested is not None:
        trace.append(TraceStep(label="suggested order quantity", value=f"{suggested} {ing.unit}",
                               source=f"projected consumption across the {lead_time + margin}-day gap (REQ-008)"))
    if gap:
        trace.append(TraceStep(label="data gap", value=gap, source="reference data"))

    return StockoutRisk(
        ingredient_id=ingredient_id,
        ingredient_name=ing.name,
        unit=ing.unit,
        supplier_id=ing.supplier_id,
        supplier_name=supplier.name if supplier else None,
        lead_time_days=lead_time,
        safety_margin_days=margin,
        quantity_on_hand=on_hand,
        projected_stockout_date=stockout_date,
        order_by_date=order_by,
        days_until_order_by=days_until,
        suggested_order_quantity=suggested,
        severity=severity,
        data_gap=gap,
        trace=trace,
    )


def assess_spoilage(ingredient_id: str, demand: IngredientDemand, as_of: date,
                    threshold_paise: int) -> SpoilageRisk | None:
    """REQ-010 to REQ-012, REQ-042."""
    ds = dataset()
    ing = ds.ingredient(ingredient_id)
    stock = ds.stock_for(ingredient_id)
    if ing is None or stock is None or not ing.perishable or stock.use_by_date is None:
        return None  # REQ-010 — a non-perishable ingredient is never flagged

    consumed = sum((d.quantity for d in demand.daily if d.on <= stock.use_by_date), ZERO)
    unconsumed = stock.quantity - consumed
    if unconsumed <= ZERO:
        return None  # it will all be used in time

    # REQ-011 — waste cost = unconsumed quantity x unit cost, in paise (ADR-008)
    waste = int((unconsumed * Decimal(ing.unit_cost_paise)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    severity = spoilage_severity(waste)
    suppressed = waste < threshold_paise   # REQ-012

    trace = [
        TraceStep(label="quantity on hand", value=f"{stock.quantity} {ing.unit}", source="current stock"),
        TraceStep(label="use-by date", value=stock.use_by_date.isoformat(), source="current stock"),
        TraceStep(label="projected consumption by use-by",
                  value=f"{consumed.quantize(Decimal('0.001'))} {ing.unit}",
                  source="demand projection summed to the use-by date (REQ-010)"),
        TraceStep(label="unconsumed quantity",
                  value=f"{unconsumed.quantize(Decimal('0.001'))} {ing.unit}",
                  source="stock on hand - projected consumption"),
        TraceStep(label="unit cost", value=rupees(ing.unit_cost_paise), source="ingredient master data"),
        TraceStep(label="estimated waste cost", value=rupees(waste),
                  source="unconsumed quantity x unit cost (REQ-011)"),
        TraceStep(label="severity", value=severity.value,
                  source=f"waste cost banding: >= {rupees(SPOILAGE_CRITICAL_PAISE)} Critical, "
                         f">= {rupees(SPOILAGE_HIGH_PAISE)} High (REQ-042)"),
        TraceStep(label="materiality", value="suppressed from the list" if suppressed else "shown",
                  source=f"threshold {rupees(threshold_paise)} (REQ-012); "
                         f"counts toward total exposure either way (REQ-027)"),
    ]

    return SpoilageRisk(
        ingredient_id=ingredient_id,
        ingredient_name=ing.name,
        unit=ing.unit,
        quantity_on_hand=stock.quantity,
        use_by_date=stock.use_by_date,
        projected_consumption_by_use_by=consumed.quantize(Decimal("0.001")),
        unconsumed_quantity=unconsumed.quantize(Decimal("0.001")),
        unit_cost_paise=ing.unit_cost_paise,
        waste_cost_paise=waste,
        severity=severity,
        suppressed=suppressed,
        trace=trace,
    )


def assess_all(as_of: date, horizon: int, threshold_paise: int,
               overlay: dict | None = None) -> tuple[dict[str, StockoutRisk], dict[str, SpoilageRisk]]:
    demands = all_ingredient_demand(as_of, horizon, overlay)
    stockouts, spoilages = {}, {}
    for ingredient_id in sorted(demands):
        demand = demands[ingredient_id]
        so = assess_stockout(ingredient_id, demand, as_of)
        if so:
            stockouts[ingredient_id] = so
        sp = assess_spoilage(ingredient_id, demand, as_of, threshold_paise)
        if sp:
            spoilages[ingredient_id] = sp
    return stockouts, spoilages


def build_listing(as_of: date | None = None, horizon: int | None = None,
                  threshold_paise: int | None = None, overlay: dict | None = None) -> RiskListing:
    """REQ-023 to REQ-027 — the single severity-ordered risk dashboard."""
    as_of = as_of or config.today()
    horizon = horizon or config.horizon_days()
    threshold_paise = threshold_paise if threshold_paise is not None else config.materiality_threshold_paise()

    stockouts, spoilages = assess_all(as_of, horizon, threshold_paise, overlay)

    rows: list[RiskRow] = []
    for r in stockouts.values():
        rows.append(RiskRow(
            ingredient_id=r.ingredient_id, ingredient_name=r.ingredient_name,
            risk_type="stockout", severity=r.severity, severity_label=r.severity.value,
            order_by_date=r.order_by_date, days_until_order_by=r.days_until_order_by,
            unit=r.unit,
        ))
    for r in spoilages.values():
        if r.suppressed:
            continue  # REQ-012 — below the materiality threshold, not shown
        rows.append(RiskRow(
            ingredient_id=r.ingredient_id, ingredient_name=r.ingredient_name,
            risk_type="spoilage", severity=r.severity, severity_label=r.severity.value,
            waste_cost_paise=r.waste_cost_paise, unit=r.unit,
        ))

    rows = rank(rows)

    # REQ-027 — the aggregate sums EVERY spoilage warning, including the ones
    # suppressed from the list above. This is what makes it invariant under a
    # threshold change (ADR-014).
    exposure = sum(r.waste_cost_paise for r in spoilages.values())
    suppressed = sum(1 for r in spoilages.values() if r.suppressed)

    gaps = [f"{g.entity_id}: {g.detail}" for g in dataset().gaps]
    gaps += [f"{r.ingredient_name}: {r.data_gap}" for r in stockouts.values() if r.data_gap]

    return RiskListing(
        as_of=as_of, horizon_days=horizon, rows=rows,
        total_waste_exposure_paise=exposure, suppressed_count=suppressed,
        materiality_threshold_paise=threshold_paise, data_gaps=sorted(set(gaps)),
    )


def rank(rows: list[RiskRow]) -> list[RiskRow]:
    """REQ-023 — band first, then urgency within band, the two types interleaved.

    Within a band, stockout rows rank by proximity to the order-by date and
    spoilage rows by waste cost. REQ-023 does not state how a stockout and a
    spoilage row of equal within-type rank order against each other, so each
    type is ranked internally and the two sequences are merged by that rank
    position, with the ingredient name as the final deterministic tiebreak.
    Documented as a gap in architecture.md 12 rather than silently invented.
    """
    ranked: list[tuple[tuple, RiskRow]] = []
    for band in (Severity.CRITICAL, Severity.HIGH, Severity.LOW):
        in_band = [r for r in rows if r.severity is band]
        stock_rows = sorted(
            [r for r in in_band if r.risk_type == "stockout"],
            key=lambda r: (r.days_until_order_by if r.days_until_order_by is not None else -999,
                           r.ingredient_name),
        )
        spoil_rows = sorted(
            [r for r in in_band if r.risk_type == "spoilage"],
            key=lambda r: (-(r.waste_cost_paise or 0), r.ingredient_name),
        )
        for position, row in enumerate(stock_rows):
            ranked.append(((band.rank, position, 0, row.ingredient_name), row))
        for position, row in enumerate(spoil_rows):
            ranked.append(((band.rank, position, 1, row.ingredient_name), row))
    ranked.sort(key=lambda pair: pair[0])
    return [row for _key, row in ranked]


def rupees(paise: int) -> str:
    """REQ-035 — INR, Indian digit grouping."""
    whole, fraction = divmod(abs(int(paise)), 100)
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        digits = ",".join(parts + [tail])
    sign = "-" if paise < 0 else ""
    return f"{sign}Rs {digits}.{fraction:02d}"
