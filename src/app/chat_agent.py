"""comp-chat-agent — REQ-013 to REQ-017, REQ-030, REQ-031, REQ-036.

One surface serves both capabilities (REQ-036): the caller does not choose
between "explain" and "what-if", an intent classifier routes the question.

ADR-006 — the language layer never computes a number. Everything this module
says is read out of a figure some engine already computed and already showed
on the dashboard, which is what makes REQ-030 and REQ-031 hold by
construction rather than by review. The intent parser below is deliberately
deterministic (keywords and a date grammar, no model call): it needs no
credentials, it cannot hallucinate, and it satisfies REQ-033 trivially.

`PHRASING_BACKEND=bedrock` swaps in Amazon Bedrock for the *prose only* — it
is handed the same pre-computed figures and is never given raw input data.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from . import config, scenario
from .demand_engine import ingredient_demand
from .reference_data import dataset
from .risk_engine import assess_spoilage, assess_stockout, rupees

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

WHATIF_MARKERS = ("what if", "what-if", "if we", "suppose", "banquet", "booking",
                  "add ", "extra ", "additional", "special")
EXPLAIN_MARKERS = ("why", "explain", "how come", "reason", "what's driving", "whats driving")


def answer(question: str, ingredient_id: str | None = None) -> dict[str, Any]:
    """Route one natural-language turn. REQ-013 + REQ-017 through one door."""
    text = (question or "").strip()
    if not text:
        return _cannot("Ask me why an ingredient is flagged, or pose a menu change "
                       "such as \"what if we add a 50-cover banquet of Chicken Dum Biryani next Saturday?\"")

    lowered = text.lower()
    is_whatif = any(m in lowered for m in WHATIF_MARKERS) and _find_dish(lowered) is not None
    if is_whatif:
        return _what_if(text, lowered)
    if any(m in lowered for m in EXPLAIN_MARKERS) or ingredient_id:
        return _explain(text, lowered, ingredient_id)
    target = _find_ingredient(lowered)
    if target:
        return _explain(text, lowered, target)
    return _cannot(
        "I could not tell whether that is a question about a flagged ingredient or a menu change. "
        "Name an ingredient (\"why is Prawns flagged?\") or a dish and a cover count "
        "(\"what if we add 50 covers of Butter Chicken next Saturday?\")."
    )


# --- explanation (REQ-013 to REQ-016) ----------------------------------------


def _explain(text: str, lowered: str, ingredient_id: str | None) -> dict[str, Any]:
    ds = dataset()
    ingredient_id = ingredient_id or _find_ingredient(lowered)
    if not ingredient_id:
        return _cannot("I could not match that to an ingredient on the menu. "
                       "Name it as it appears on the dashboard, for example \"why is Paneer flagged?\"")

    ing = ds.ingredient(ingredient_id)
    as_of = config.today()
    horizon = config.horizon_days()
    demand = ingredient_demand(ingredient_id, as_of, horizon)
    stockout = assess_stockout(ingredient_id, demand, as_of)
    spoilage = assess_spoilage(ingredient_id, demand, as_of, config.materiality_threshold_paise())

    if not stockout and not spoilage:
        return {
            "intent": "explain",
            "ingredient_id": ingredient_id,
            "answer": f"{ing.name} is not currently flagged. Projected consumption over the next "
                      f"{horizon} days is {demand.total} {ing.unit} against "
                      f"{ds.stock_for(ingredient_id).quantity} {ing.unit} on hand, and it is expected "
                      f"to be used before any use-by date.",
            "figures": [], "trace": demand.trace, "contributions": demand.contributions,
        }

    figures: list[dict[str, str]] = []
    lines: list[str] = []

    # REQ-014 — contributing dishes and each one's relative share
    top = demand.contributions[:4]
    if top:
        named = ", ".join(f"{c.dish_name} ({c.share_pct}%)" for c in top)
        lines.append(f"{ing.name} is drawn by {len(demand.contributions)} dishes. "
                     f"The largest contributors are {named}.")
        for c in top:
            figures.append({"label": f"{c.dish_name} share", "value": f"{c.share_pct}%"})

    if stockout:
        # REQ-015 dates, REQ-016 supplier lead time
        lines.append(
            f"Projected consumption of {demand.total} {ing.unit} over the next {horizon} days "
            f"exhausts the {stockout.quantity_on_hand} {ing.unit} on hand on "
            f"{stockout.projected_stockout_date.isoformat()}."
        )
        figures.append({"label": "projected stockout date",
                        "value": stockout.projected_stockout_date.isoformat()})
        if stockout.order_by_date:
            days = stockout.days_until_order_by
            when = (f"{days} days away" if days > 1 else
                    "tomorrow" if days == 1 else
                    "today" if days == 0 else
                    f"{abs(days)} days ago, so it is already overdue")
            lines.append(
                f"{stockout.supplier_name} takes {stockout.lead_time_days} days to deliver, and this "
                f"ingredient carries a {stockout.safety_margin_days}-day safety margin, so the order-by "
                f"date is {stockout.order_by_date.isoformat()} — {when}, "
                f"which is why it is banded {stockout.severity.value}."
            )
            figures += [
                {"label": "order-by date", "value": stockout.order_by_date.isoformat()},
                {"label": "supplier lead time", "value": f"{stockout.lead_time_days} days"},
                {"label": "safety margin", "value": f"{stockout.safety_margin_days} days"},
                {"label": "severity", "value": stockout.severity.value},
            ]
            if stockout.suggested_order_quantity is not None:
                lines.append(f"Suggested order quantity is {stockout.suggested_order_quantity} {ing.unit}, "
                             f"covering consumption across that gap.")
                figures.append({"label": "suggested order quantity",
                                "value": f"{stockout.suggested_order_quantity} {ing.unit}"})
        elif stockout.data_gap:
            lines.append(f"No order-by date could be computed: {stockout.data_gap}.")

    if spoilage:
        lines.append(
            f"Separately, {spoilage.quantity_on_hand} {ing.unit} is on hand against a use-by date of "
            f"{spoilage.use_by_date.isoformat()}, and only {spoilage.projected_consumption_by_use_by} "
            f"{ing.unit} is projected to be used by then. That leaves "
            f"{spoilage.unconsumed_quantity} {ing.unit} at {rupees(spoilage.unit_cost_paise)} per "
            f"{ing.unit}, an estimated waste cost of {rupees(spoilage.waste_cost_paise)} — "
            f"banded {spoilage.severity.value}."
        )
        figures += [
            {"label": "use-by date", "value": spoilage.use_by_date.isoformat()},
            {"label": "estimated waste cost", "value": rupees(spoilage.waste_cost_paise)},
            {"label": "severity", "value": spoilage.severity.value},
        ]

    trace = (stockout.trace if stockout else []) + (spoilage.trace if spoilage else [])
    prose = _phrase("\n\n".join(lines), figures)
    return {
        "intent": "explain",
        "ingredient_id": ingredient_id,
        "answer": prose,
        "figures": figures,
        "trace": demand.trace + trace,
        "contributions": demand.contributions,
    }


# --- what-if (REQ-017 to REQ-020) --------------------------------------------


def _what_if(text: str, lowered: str) -> dict[str, Any]:
    dish_id = _find_dish(lowered)
    ds = dataset()
    dish = ds.dish(dish_id) if dish_id else None
    if not dish:
        return _cannot("I could not match a dish on the menu in that scenario. "
                       "Name the dish as it appears on the menu.")

    servings = _find_servings(lowered)
    if servings is None:
        return _cannot(f"How many additional covers of {dish.name}? "
                       f"For example: \"what if we add a 50-cover banquet of {dish.name} next Saturday?\"")

    date_from, date_to, when_said = _find_dates(lowered)
    result = scenario.preview(dish.dish_id, dish.name, servings, date_from, date_to)

    lines = [f"Adding {servings} covers of {dish.name} {when_said} "
             f"({date_from.isoformat()}{'' if date_from == date_to else ' to ' + date_to.isoformat()}):"]

    if result["newly_at_risk"]:
        for row in result["newly_at_risk"]:
            detail = (f"order by {row['order_by_date']}" if row["order_by_date"]
                      else (row["waste_cost"] or ""))
            lines.append(f"- {row['ingredient_name']} newly becomes a {row['risk_type']} risk "
                         f"({row['severity']}{', ' + detail if detail else ''}).")
    else:
        lines.append("- No ingredient newly becomes at risk.")

    if result["order_by_dates_moved"]:
        for row in result["order_by_dates_moved"]:
            lines.append(f"- {row['ingredient_name']} order-by moves {row['direction']} by "
                         f"{abs(row['days_moved'])} day(s), from {row['was']} to {row['now']}.")
    else:
        lines.append("- No order-by date changes.")

    exposure = result["waste_exposure"]
    lines.append(f"- Total waste exposure {exposure['direction']}"
                 f"{'' if exposure['delta_paise'] == 0 else ' by ' + rupees(abs(exposure['delta_paise']))}"
                 f", from {exposure['before']} to {exposure['after']}.")

    if result["no_longer_at_risk"]:
        for row in result["no_longer_at_risk"]:
            lines.append(f"- {row['ingredient_name']} is no longer a {row['risk_type']} risk.")

    figures = [{"label": "waste exposure after", "value": exposure["after"]},
               {"label": "change", "value": exposure["delta"]}]
    return {
        "intent": "what_if",
        "answer": "\n".join(lines),
        "figures": figures,
        "scenario": result["scenario"],
        "newly_at_risk": result["newly_at_risk"],
        "order_by_dates_moved": result["order_by_dates_moved"],
        "waste_exposure": exposure,
        "listing": result["listing"],
    }


# --- parsing helpers ---------------------------------------------------------


def _find_dish(lowered: str) -> str | None:
    ds = dataset()
    best: tuple[int, str] | None = None
    for dish in ds.dishes:
        name = dish.name.lower()
        if name in lowered:
            if best is None or len(name) > best[0]:
                best = (len(name), dish.dish_id)
    if best:
        return best[1]
    # fall back to a distinctive word, e.g. "biryani" when only one dish has it
    for dish in ds.dishes:
        words = [w for w in dish.name.lower().split() if len(w) > 4]
        matches = [d for d in ds.dishes if any(w in d.name.lower() for w in words)]
        if words and all(w in lowered for w in words[-1:]) and len(matches) == 1:
            return dish.dish_id
    return None


def _find_ingredient(lowered: str) -> str | None:
    ds = dataset()
    best: tuple[int, str] | None = None
    for ing in ds.ingredients:
        name = ing.name.lower()
        if name in lowered and (best is None or len(name) > best[0]):
            best = (len(name), ing.ingredient_id)
    return best[1] if best else None


def _find_servings(lowered: str) -> Decimal | None:
    match = re.search(r"(\d+)\s*(?:-|\s)?\s*(?:cover|serving|portion|plate|pax|guest)", lowered)
    if not match:
        match = re.search(r"(?:add|extra|additional|another)\s+(\d+)", lowered)
    if not match:
        match = re.search(r"\b(\d{1,4})\b", lowered)
    return Decimal(match.group(1)) if match else None


def _find_dates(lowered: str) -> tuple[date, date, str]:
    """A small, explicit date grammar. Unrecognised phrasing falls back to
    tomorrow, and the answer always states the dates it actually used so the
    manager can see whether it understood them."""
    today = config.today()
    horizon = config.horizon_days()

    match = re.search(r"next (\d+) days", lowered)
    if match:
        span = min(int(match.group(1)), horizon)
        return today + timedelta(days=1), today + timedelta(days=span), f"over the next {span} days"

    if "this weekend" in lowered or "the weekend" in lowered:
        saturday = _next_weekday(today, 5)
        return saturday, saturday + timedelta(days=1), "this weekend"

    for index, name in enumerate(WEEKDAYS):
        if name in lowered:
            day = _next_weekday(today, index)
            return day, day, f"on {name.capitalize()} {day.isoformat()}"

    if "tomorrow" in lowered:
        return today + timedelta(days=1), today + timedelta(days=1), "tomorrow"
    if "next week" in lowered:
        start = _next_weekday(today, 0)
        return start, start + timedelta(days=6), "next week"

    fallback = today + timedelta(days=1)
    return fallback, fallback, "tomorrow (no date given, so the soonest day was used)"


def _next_weekday(from_date: date, weekday: int) -> date:
    ahead = (weekday - from_date.weekday()) % 7
    return from_date + timedelta(days=ahead or 7)


def _cannot(message: str) -> dict[str, Any]:
    """journeys.md flags unparseable input as a PRD gap with no defined
    behaviour. Saying plainly what was not understood is the safe reading: it
    never invents a figure, which REQ-030 forbids."""
    return {"intent": "unrecognised", "answer": message, "figures": [], "trace": []}


def _phrase(text: str, figures: list[dict[str, str]]) -> str:
    """Optional Bedrock pass over the *prose only* (ADR-006/ADR-007).

    The model is handed the already-composed answer and the exact figure set,
    and is instructed to reword without introducing a number. Any numeral it
    emits that is not in the supplied set fails the check and the deterministic
    text is returned instead.
    """
    if os.environ.get("PHRASING_BACKEND") != "bedrock":
        return text
    try:
        import json

        import boto3

        client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
        model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
        prompt = (
            "Reword the following kitchen-management explanation to read naturally. "
            "You may not introduce, change, remove or round any number, date or currency amount. "
            "Use only the figures given.\n\n"
            f"FIGURES: {json.dumps(figures)}\n\nTEXT:\n{text}"
        )
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            }),
        )
        candidate = json.loads(response["body"].read())["content"][0]["text"].strip()
        if _numbers_within(candidate, text):
            return candidate
    except Exception:
        pass  # REQ-030/REQ-031 matter more than phrasing; fall back silently
    return text


def _numbers_within(candidate: str, source: str) -> bool:
    allowed = set(re.findall(r"\d[\d,.]*", source))
    return all(token in allowed for token in re.findall(r"\d[\d,.]*", candidate))
