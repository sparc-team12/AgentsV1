"""comp-reference-data — loads, validates and serves the six supplied datasets.

REQ-037 - REQ-041. The datasets are supplied and fixed (PRD "Input Data"), so
they ship with the build as JSON and are loaded once. Validation gaps are
surfaced, never silently repaired: a recipe naming an unknown ingredient, an
ingredient with no supplier, a perishable with no use-by date and an
ingredient with no safety margin are each flagged (US-025..US-028).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from functools import lru_cache

from . import config
from .domain import Dish, Ingredient, Recipe, SalesRecord, StockOnHand, Supplier


@dataclass(frozen=True)
class Gap:
    category: str
    entity_id: str
    detail: str


@dataclass
class Dataset:
    dishes: list[Dish] = field(default_factory=list)
    recipes: list[Recipe] = field(default_factory=list)
    ingredients: list[Ingredient] = field(default_factory=list)
    suppliers: list[Supplier] = field(default_factory=list)
    stock: list[StockOnHand] = field(default_factory=list)
    sales: list[SalesRecord] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)

    # --- lookups ---
    def dish(self, dish_id: str) -> Dish | None:
        return self._by_dish.get(dish_id)

    def ingredient(self, ingredient_id: str) -> Ingredient | None:
        return self._by_ingredient.get(ingredient_id)

    def supplier(self, supplier_id: str | None) -> Supplier | None:
        return self._by_supplier.get(supplier_id) if supplier_id else None

    def stock_for(self, ingredient_id: str) -> StockOnHand | None:
        return self._by_stock.get(ingredient_id)

    def recipes_for_ingredient(self, ingredient_id: str) -> list[Recipe]:
        return self._recipes_by_ingredient.get(ingredient_id, [])

    def sales_for(self, dish_id: str) -> list[SalesRecord]:
        return self._sales_by_dish.get(dish_id, [])

    def safety_margin_days(self, ingredient: Ingredient) -> int | None:
        """REQ-007 / REQ-039 — ingredient first, then supplier, else *missing*.

        Never defaults to zero. A missing margin is a data gap the manager has
        to fix, not a silently-assumed value (US-004 AC-3, US-026 AC-5).
        """
        if ingredient.safety_margin_days is not None:
            return ingredient.safety_margin_days
        supplier = self.supplier(ingredient.supplier_id)
        if supplier and supplier.safety_margin_days is not None:
            return supplier.safety_margin_days
        return None

    def index(self) -> "Dataset":
        self._by_dish = {d.dish_id: d for d in self.dishes}
        self._by_ingredient = {i.ingredient_id: i for i in self.ingredients}
        self._by_supplier = {s.supplier_id: s for s in self.suppliers}
        self._by_stock = {s.ingredient_id: s for s in self.stock}
        self._recipes_by_ingredient = {}
        for r in self.recipes:
            self._recipes_by_ingredient.setdefault(r.ingredient_id, []).append(r)
        self._sales_by_dish = {}
        for s in self.sales:
            self._sales_by_dish.setdefault(s.dish_id, []).append(s)
        for rows in self._sales_by_dish.values():
            rows.sort(key=lambda r: r.sale_date)
        return self

    def load_status(self) -> list[dict]:
        """REQ-037 — what the Data Setup hub shows."""
        gaps_by_category: dict[str, int] = {}
        for gap in self.gaps:
            gaps_by_category[gap.category] = gaps_by_category.get(gap.category, 0) + 1
        categories = [
            ("menu", "Menu & Recipe Setup", len(self.dishes), "dishes"),
            ("ingredients", "Ingredients & Suppliers Setup", len(self.ingredients), "ingredients"),
            ("stock", "Current Stock Setup", len(self.stock), "stock rows"),
            ("sales-history", "Sales History Import", len(self.sales), "sales rows"),
        ]
        return [
            {
                "key": key,
                "title": title,
                "loaded": count > 0,
                "record_count": count,
                "record_label": label,
                "gap_count": gaps_by_category.get(key, 0),
            }
            for key, title, count, label in categories
        ]


def _read(name: str) -> list[dict]:
    path = config.DATA_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(ds: Dataset) -> None:
    ingredient_ids = {i.ingredient_id for i in ds.ingredients}
    supplier_ids = {s.supplier_id for s in ds.suppliers}
    dish_ids = {d.dish_id for d in ds.dishes}

    for r in ds.recipes:
        if r.ingredient_id not in ingredient_ids:
            ds.gaps.append(Gap("menu", r.recipe_id,
                               f"recipe references unknown ingredient {r.ingredient_id}"))
        if r.dish_id not in dish_ids:
            ds.gaps.append(Gap("menu", r.recipe_id, f"recipe references unknown dish {r.dish_id}"))

    for i in ds.ingredients:
        if not i.supplier_id or i.supplier_id not in supplier_ids:
            ds.gaps.append(Gap("ingredients", i.ingredient_id, f"{i.name} has no mapped supplier"))
        if ds.safety_margin_days(i) is None:
            ds.gaps.append(Gap("ingredients", i.ingredient_id,
                               f"{i.name} has no safety margin on the ingredient or its supplier"))

    stocked = {s.ingredient_id for s in ds.stock}
    for i in ds.ingredients:
        if i.ingredient_id not in stocked:
            ds.gaps.append(Gap("stock", i.ingredient_id, f"{i.name} has no current stock row"))
    for s in ds.stock:
        ing = ds.ingredient(s.ingredient_id)
        if ing and ing.perishable and s.use_by_date is None:
            ds.gaps.append(Gap("stock", s.ingredient_id,
                               f"{ing.name} is perishable but has no use-by date"))

    # REQ-041 — 12 weeks of history per dish
    expected_days = 12 * 7
    for d in ds.dishes:
        rows = ds.sales_for(d.dish_id)
        if len(rows) < expected_days:
            ds.gaps.append(Gap("sales-history", d.dish_id,
                               f"{d.name} has {len(rows)} days of history, expected {expected_days}"))


@lru_cache(maxsize=1)
def dataset() -> Dataset:
    ds = Dataset(
        dishes=[Dish(**row) for row in _read("dishes.json")],
        recipes=[Recipe(**row) for row in _read("recipes.json")],
        ingredients=[Ingredient(**row) for row in _read("ingredients.json")],
        suppliers=[Supplier(**row) for row in _read("suppliers.json")],
        stock=[StockOnHand(**row) for row in _read("current_stock.json")],
        sales=[SalesRecord(**row) for row in _read("sales_history.json")],
    ).index()
    _validate(ds)
    return ds


def reset_cache() -> None:
    dataset.cache_clear()


def history_window(ds: Dataset) -> tuple[date | None, date | None]:
    if not ds.sales:
        return None, None
    dates = [s.sale_date for s in ds.sales]
    return min(dates), max(dates)


def quantity(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))
