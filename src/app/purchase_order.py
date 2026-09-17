"""comp-purchase-order — REQ-021, REQ-022.

Produces an editable text draft. It is never sent: the PRD's Non-Goals exclude
every procurement integration, so the draft exists to be copied out of the
system by the manager through their own channel.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import config
from .demand_engine import ingredient_demand
from .reference_data import dataset
from .risk_engine import assess_stockout


def draft(ingredient_id: str, as_of: date | None = None) -> dict:
    as_of = as_of or config.today()
    ds = dataset()
    ing = ds.ingredient(ingredient_id)
    if ing is None:
        return {"error": f"unknown ingredient {ingredient_id}"}

    demand = ingredient_demand(ingredient_id, as_of, config.horizon_days())
    risk = assess_stockout(ingredient_id, demand, as_of)
    if risk is None:
        return {"error": f"{ing.name} is not at stockout risk, so there is nothing to order"}

    supplier = ds.supplier(ing.supplier_id)
    required_by = risk.projected_stockout_date
    if risk.lead_time_days is not None:
        # deliver before stock runs out, allowing the supplier its full lead time
        required_by = risk.projected_stockout_date - timedelta(days=1)

    body = "\n".join([
        f"To: {supplier.name if supplier else 'SUPPLIER NOT MAPPED'}",
        f"Date: {as_of.isoformat()}",
        "",
        "Please supply the following:",
        "",
        f"  Item:              {ing.name}",
        f"  Quantity:          {risk.suggested_order_quantity or 'TBC'} {ing.unit}",
        f"  Required delivery: {required_by.isoformat()}",
        "",
        f"Our stock is projected to run out on {risk.projected_stockout_date.isoformat()}."
        + (f" Order-by date {risk.order_by_date.isoformat()} "
           f"(lead time {risk.lead_time_days} days, safety margin {risk.safety_margin_days} days)."
           if risk.order_by_date else ""),
        "",
        "Kind regards,",
        "Kitchen Manager",
    ])

    return {
        "ingredient_id": ingredient_id,
        "supplier_name": supplier.name if supplier else None,
        "item": ing.name,
        "quantity": str(risk.suggested_order_quantity) if risk.suggested_order_quantity else None,
        "unit": ing.unit,
        "required_delivery_date": required_by.isoformat(),
        "body_text": body,
        "note": "Editable draft. Nothing is sent from this system (REQ-022).",
    }
