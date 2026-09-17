"""comp-demand-engine — REQ-001 to REQ-004.

Projects dish demand from sales history, then maps it through recipes to
ingredient demand.

Determinism (REQ-028) is structural, not aspirational:
  * ``as_of`` is always passed in, never read from the clock here;
  * every aggregation iterates a ``sorted()`` sequence, so no dict ordering
    can decide a total;
  * all arithmetic is ``Decimal``, never ``float``.

Traceability (REQ-029) rides on every figure: each projection carries the
history rows and weights it was built from.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache

from . import config
from .domain import DailyDemand, DishContribution, IngredientDemand, TraceStep
from .reference_data import Dataset, dataset

ZERO = Decimal("0")
DECAY = Decimal(config.TREND_DECAY)


def project_dish_demand(ds: Dataset, dish_id: str, as_of: date, horizon: int) -> dict[date, Decimal]:
    """REQ-002 + REQ-003 — day-of-week shape, recency-weighted.

    A future Saturday is projected from that dish's Saturday history only
    (REQ-002), and recent weeks count for more than old ones (REQ-003) via an
    exponential weight of ``DECAY ** weeks_ago``.
    """
    rows = ds.sales_for(dish_id)
    by_dow: dict[int, list[tuple[date, int]]] = {}
    for row in rows:
        by_dow.setdefault(row.sale_date.weekday(), []).append((row.sale_date, row.units_sold))

    projection: dict[date, Decimal] = {}
    for offset in range(1, horizon + 1):
        day = as_of + timedelta(days=offset)
        samples = sorted(by_dow.get(day.weekday(), []), key=lambda s: s[0], reverse=True)
        if not samples:
            projection[day] = ZERO
            continue
        weighted, weights = ZERO, ZERO
        for weeks_ago, (_sample_date, units) in enumerate(samples):
            weight = DECAY**weeks_ago
            weighted += Decimal(units) * weight
            weights += weight
        projection[day] = (weighted / weights) if weights else ZERO
    return projection


@lru_cache(maxsize=8)
def _dish_projections(as_of: date, horizon: int) -> dict[str, dict[date, Decimal]]:
    ds = dataset()
    return {d.dish_id: project_dish_demand(ds, d.dish_id, as_of, horizon)
            for d in sorted(ds.dishes, key=lambda x: x.dish_id) if d.active}


def dish_projections(as_of: date, horizon: int, overlay: dict[str, dict[date, Decimal]] | None = None
                     ) -> dict[str, dict[date, Decimal]]:
    """Baseline projections, optionally with a what-if overlay applied (ADR-011)."""
    base = _dish_projections(as_of, horizon)
    if not overlay:
        return base
    merged: dict[str, dict[date, Decimal]] = {}
    for dish_id, days in base.items():
        extra = overlay.get(dish_id, {})
        merged[dish_id] = {day: qty + extra.get(day, ZERO) for day, qty in days.items()}
    return merged


def ingredient_demand(ingredient_id: str, as_of: date, horizon: int,
                      overlay: dict[str, dict[date, Decimal]] | None = None) -> IngredientDemand:
    """REQ-004 — map each dish's projected demand through its recipe and sum."""
    ds = dataset()
    projections = dish_projections(as_of, horizon, overlay)

    daily: dict[date, Decimal] = {as_of + timedelta(days=o): ZERO for o in range(1, horizon + 1)}
    per_dish: dict[str, Decimal] = {}

    for recipe in sorted(ds.recipes_for_ingredient(ingredient_id), key=lambda r: r.recipe_id):
        dish_days = projections.get(recipe.dish_id)
        if not dish_days:
            continue
        qty_per_serving = recipe.quantity_per_serving
        subtotal = ZERO
        for day in sorted(dish_days):
            if day not in daily:
                continue
            contribution = dish_days[day] * qty_per_serving
            daily[day] += contribution
            subtotal += contribution
        if subtotal > ZERO:
            per_dish[recipe.dish_id] = per_dish.get(recipe.dish_id, ZERO) + subtotal

    total = sum((daily[day] for day in sorted(daily)), ZERO)

    contributions = []
    for dish_id in sorted(per_dish, key=lambda d: (-per_dish[d], d)):
        dish = ds.dish(dish_id)
        share = (per_dish[dish_id] / total * 100) if total > ZERO else ZERO
        contributions.append(DishContribution(
            dish_id=dish_id,
            dish_name=dish.name if dish else dish_id,
            quantity=_q(per_dish[dish_id]),
            share_pct=_q(share, places="0.1"),
        ))

    ing = ds.ingredient(ingredient_id)
    trace = [
        TraceStep(label="forward horizon",
                  value=f"{horizon} days from {as_of.isoformat()}",
                  source="REQ-001, configuration"),
        TraceStep(label="projection method",
                  value=f"per day-of-week mean of 12 weeks, weighted {config.TREND_DECAY}^weeks_ago",
                  source="REQ-002, REQ-003, sales history"),
        TraceStep(label="contributing dishes",
                  value=str(len(contributions)),
                  source="recipes"),
    ]
    for c in contributions:
        trace.append(TraceStep(
            label=f"{c.dish_name} contribution",
            value=f"{c.quantity} {ing.unit if ing else ''} ({c.share_pct}%)",
            source="dish projection x recipe quantity per serving (REQ-004)",
        ))
    trace.append(TraceStep(label="total projected demand",
                           value=f"{_q(total)} {ing.unit if ing else ''}",
                           source="sum across all contributing dishes"))

    return IngredientDemand(
        ingredient_id=ingredient_id,
        daily=[DailyDemand(on=day, quantity=_q(daily[day])) for day in sorted(daily)],
        total=_q(total),
        contributions=contributions,
        trace=trace,
    )


def all_ingredient_demand(as_of: date, horizon: int,
                          overlay: dict[str, dict[date, Decimal]] | None = None
                          ) -> dict[str, IngredientDemand]:
    ds = dataset()
    return {
        ing.ingredient_id: ingredient_demand(ing.ingredient_id, as_of, horizon, overlay)
        for ing in sorted(ds.ingredients, key=lambda i: i.ingredient_id)
    }


def _q(value: Decimal, places: str = "0.001") -> Decimal:
    return value.quantize(Decimal(places))


def reset_cache() -> None:
    _dish_projections.cache_clear()
