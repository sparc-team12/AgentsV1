"""comp-reference-data — the canonical domain types.

Every other module imports these. Names come from the PRD Glossary verbatim
(Dish, Recipe, Ingredient, Supplier, Stock on hand, Sales history, Severity,
Order-by date, Waste cost, ...). Vocabulary drift here breaks every downstream
search, so do not rename anything without amending the PRD Glossary first.

ADR-008: all money is an integer count of paise. No float ever touches a money
value. Quantities are Decimal with an explicit scale.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Paise = int


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Severity(str, Enum):
    """REQ-009 / REQ-042 — one shared three-band scale across both risk types."""

    CRITICAL = "Critical"
    HIGH = "High"
    LOW = "Low"

    @property
    def rank(self) -> int:
        return {"Critical": 0, "High": 1, "Low": 2}[self.value]


RiskType = Literal["stockout", "spoilage"]


# --- Input Data (the six supplied categories) --------------------------------


class Dish(Frozen):
    dish_id: str
    name: str
    active: bool = True


class Recipe(Frozen):
    recipe_id: str
    dish_id: str
    ingredient_id: str
    quantity_per_serving: Decimal
    unit: str


class Ingredient(Frozen):
    ingredient_id: str
    name: str
    unit: str
    unit_cost_paise: Paise
    perishable: bool
    shelf_life_days: int | None = None
    supplier_id: str | None = None
    safety_margin_days: int | None = None


class Supplier(Frozen):
    supplier_id: str
    name: str
    lead_time_days: int
    safety_margin_days: int | None = None


class StockOnHand(Frozen):
    ingredient_id: str
    quantity: Decimal
    use_by_date: date | None = None
    snapshot_loaded_at: date | None = None


class SalesRecord(Frozen):
    dish_id: str
    sale_date: date
    units_sold: int


# --- Traceability (REQ-029, ADR-009) -----------------------------------------


class TraceStep(Frozen):
    """One line of the arithmetic trace behind a published figure."""

    label: str
    value: str
    source: str


class Traced[T](Frozen):
    """Every figure crossing a module boundary carries how it was derived.

    ADR-009: no engine returns a bare number. REQ-029 becomes a property of the
    return type rather than something a caller has to remember to ask for.
    """

    value: T
    trace: list[TraceStep] = Field(default_factory=list)


# --- Derived figures ---------------------------------------------------------


class DailyDemand(Frozen):
    on: date
    quantity: Decimal


class DishContribution(Frozen):
    """REQ-014 — a contributing dish and its relative share of the demand."""

    dish_id: str
    dish_name: str
    quantity: Decimal
    share_pct: Decimal


class IngredientDemand(Frozen):
    ingredient_id: str
    daily: list[DailyDemand]
    total: Decimal
    contributions: list[DishContribution]
    trace: list[TraceStep] = Field(default_factory=list)


class StockoutRisk(Frozen):
    ingredient_id: str
    ingredient_name: str
    unit: str
    supplier_id: str | None
    supplier_name: str | None
    lead_time_days: int | None
    safety_margin_days: int | None
    quantity_on_hand: Decimal
    projected_stockout_date: date
    order_by_date: date | None
    days_until_order_by: int | None
    suggested_order_quantity: Decimal | None
    severity: Severity
    data_gap: str | None = None
    trace: list[TraceStep] = Field(default_factory=list)


class SpoilageRisk(Frozen):
    ingredient_id: str
    ingredient_name: str
    unit: str
    quantity_on_hand: Decimal
    use_by_date: date
    projected_consumption_by_use_by: Decimal
    unconsumed_quantity: Decimal
    unit_cost_paise: Paise
    waste_cost_paise: Paise
    severity: Severity
    suppressed: bool
    trace: list[TraceStep] = Field(default_factory=list)


class RiskRow(Frozen):
    """One line of the risk dashboard (REQ-023 - REQ-026)."""

    ingredient_id: str
    ingredient_name: str
    risk_type: RiskType
    severity: Severity
    severity_label: str          # REQ-034: text, not only colour
    order_by_date: date | None = None
    days_until_order_by: int | None = None
    waste_cost_paise: Paise | None = None
    unit: str = ""


class RiskListing(Frozen):
    as_of: date
    horizon_days: int
    rows: list[RiskRow]
    total_waste_exposure_paise: Paise   # REQ-027, includes suppressed warnings
    suppressed_count: int
    materiality_threshold_paise: Paise
    data_gaps: list[str] = Field(default_factory=list)
