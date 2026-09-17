"""Generate the six supplied Input Data datasets as JSON.

The PRD states all input data is *supplied*, fixed, and never inferred by the
system. This script stands in for the client's dataset so the build has
something to run against. It is deterministic (fixed RNG seed), so re-running
it produces byte-identical files and never perturbs a demo.

Run:  python scripts/seed_data.py
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "src" / "data"
TODAY = date(2026, 9, 18)
HISTORY_WEEKS = 12
RNG = random.Random(42)

SUPPLIERS = [
    {"supplier_id": "SUP-1", "name": "Green Valley Produce", "lead_time_days": 2, "safety_margin_days": 1},
    {"supplier_id": "SUP-2", "name": "Coastal Meat & Poultry", "lead_time_days": 3, "safety_margin_days": 2},
    {"supplier_id": "SUP-3", "name": "Deccan Dry Goods", "lead_time_days": 5, "safety_margin_days": 2},
    {"supplier_id": "SUP-4", "name": "Nandini Dairy Direct", "lead_time_days": 1, "safety_margin_days": 1},
]

# name, unit, unit_cost_paise, perishable, shelf_life_days, supplier, safety_margin override
INGREDIENTS = [
    ("Basmati Rice", "kg", 12500, False, None, "SUP-3", None),
    ("Chicken Thigh", "kg", 28000, True, 4, "SUP-2", None),
    ("Mutton Shoulder", "kg", 68000, True, 4, "SUP-2", 3),
    ("Prawns", "kg", 72000, True, 2, "SUP-2", 3),
    ("Paneer", "kg", 42000, True, 5, "SUP-4", None),
    ("Full Cream Milk", "l", 6600, True, 3, "SUP-4", None),
    ("Fresh Cream", "l", 24000, True, 5, "SUP-4", None),
    ("Butter", "kg", 52000, True, 20, "SUP-4", None),
    ("Curd", "kg", 8000, True, 4, "SUP-4", None),
    ("Tomato", "kg", 4200, True, 5, "SUP-1", None),
    ("Onion", "kg", 3400, True, 14, "SUP-1", None),
    ("Ginger", "kg", 14000, True, 10, "SUP-1", None),
    ("Garlic", "kg", 16000, True, 12, "SUP-1", None),
    ("Green Chilli", "kg", 7000, True, 6, "SUP-1", None),
    ("Coriander Leaves", "kg", 9000, True, 2, "SUP-1", None),
    ("Mint Leaves", "kg", 11000, True, 2, "SUP-1", None),
    ("Curry Leaves", "kg", 13000, True, 4, "SUP-1", None),
    ("Potato", "kg", 2800, True, 20, "SUP-1", None),
    ("Cauliflower", "kg", 4000, True, 6, "SUP-1", None),
    ("Green Peas", "kg", 9500, True, 5, "SUP-1", None),
    ("Spinach", "kg", 3800, True, 3, "SUP-1", None),
    ("Capsicum", "kg", 6200, True, 7, "SUP-1", None),
    ("Lemon", "kg", 8800, True, 10, "SUP-1", None),
    ("Cashew Nuts", "kg", 86000, False, None, "SUP-3", None),
    ("Ghee", "kg", 64000, False, None, "SUP-4", None),
    ("Refined Oil", "l", 14500, False, None, "SUP-3", None),
    ("Wheat Flour", "kg", 4800, False, None, "SUP-3", None),
    ("Toor Dal", "kg", 15500, False, None, "SUP-3", None),
    ("Chana Dal", "kg", 11000, False, None, "SUP-3", None),
    ("Garam Masala", "kg", 48000, False, None, "SUP-3", None),
    ("Turmeric Powder", "kg", 22000, False, None, "SUP-3", None),
    ("Red Chilli Powder", "kg", 26000, False, None, "SUP-3", None),
    ("Coriander Powder", "kg", 19000, False, None, "SUP-3", None),
    ("Cumin Seeds", "kg", 34000, False, None, "SUP-3", None),
    ("Saffron", "kg", 2400000, False, None, "SUP-3", None),
    ("Sugar", "kg", 4600, False, None, "SUP-3", None),
    ("Salt", "kg", 2000, False, None, "SUP-3", None),
]

# dish name, base daily covers, weekend multiplier, recipe {ingredient: qty per serving}
DISHES = [
    ("Hyderabadi Mutton Biryani", 24, 1.8, {"Basmati Rice": 0.18, "Mutton Shoulder": 0.22, "Onion": 0.09,
     "Curd": 0.06, "Ghee": 0.02, "Garam Masala": 0.004, "Saffron": 0.00004, "Mint Leaves": 0.008}),
    ("Chicken Dum Biryani", 38, 1.7, {"Basmati Rice": 0.18, "Chicken Thigh": 0.20, "Onion": 0.08,
     "Curd": 0.05, "Ghee": 0.018, "Garam Masala": 0.004, "Mint Leaves": 0.007}),
    ("Butter Chicken", 30, 1.5, {"Chicken Thigh": 0.18, "Tomato": 0.14, "Butter": 0.03,
     "Fresh Cream": 0.04, "Cashew Nuts": 0.02, "Garam Masala": 0.003}),
    ("Paneer Butter Masala", 26, 1.4, {"Paneer": 0.15, "Tomato": 0.13, "Butter": 0.025,
     "Fresh Cream": 0.035, "Cashew Nuts": 0.02}),
    ("Prawn Ghee Roast", 14, 1.9, {"Prawns": 0.16, "Ghee": 0.03, "Red Chilli Powder": 0.006,
     "Curry Leaves": 0.004, "Garlic": 0.01}),
    ("Chicken Chettinad", 18, 1.4, {"Chicken Thigh": 0.19, "Onion": 0.07, "Coconut Oil": 0.0,
     "Cumin Seeds": 0.003, "Curry Leaves": 0.003, "Red Chilli Powder": 0.005}),
    ("Dal Tadka", 34, 1.2, {"Toor Dal": 0.08, "Tomato": 0.05, "Ghee": 0.012,
     "Cumin Seeds": 0.002, "Coriander Leaves": 0.004}),
    ("Palak Paneer", 20, 1.3, {"Paneer": 0.12, "Spinach": 0.18, "Fresh Cream": 0.02, "Garlic": 0.008}),
    ("Aloo Gobi", 22, 1.2, {"Potato": 0.12, "Cauliflower": 0.14, "Turmeric Powder": 0.002,
     "Coriander Powder": 0.003}),
    ("Veg Pulao", 19, 1.3, {"Basmati Rice": 0.16, "Green Peas": 0.04, "Capsicum": 0.03,
     "Ghee": 0.012, "Cashew Nuts": 0.008}),
    ("Malai Kofta", 15, 1.5, {"Paneer": 0.09, "Potato": 0.07, "Fresh Cream": 0.04,
     "Cashew Nuts": 0.025, "Tomato": 0.08}),
    ("Chicken Tikka", 28, 1.6, {"Chicken Thigh": 0.17, "Curd": 0.05, "Red Chilli Powder": 0.004,
     "Lemon": 0.01, "Garam Masala": 0.003}),
    ("Tandoori Roti", 90, 1.4, {"Wheat Flour": 0.07, "Butter": 0.004}),
    ("Jeera Rice", 30, 1.2, {"Basmati Rice": 0.15, "Cumin Seeds": 0.003, "Ghee": 0.01}),
    ("Masala Papad", 25, 1.3, {"Onion": 0.03, "Tomato": 0.03, "Green Chilli": 0.004}),
    ("Gulab Jamun", 32, 1.5, {"Full Cream Milk": 0.08, "Sugar": 0.06, "Ghee": 0.02}),
    ("Kheer", 18, 1.4, {"Full Cream Milk": 0.22, "Basmati Rice": 0.02, "Sugar": 0.05,
     "Cashew Nuts": 0.006, "Saffron": 0.00002}),
    ("Chana Masala", 21, 1.2, {"Chana Dal": 0.09, "Onion": 0.05, "Tomato": 0.07,
     "Coriander Powder": 0.003}),
]

DOW_FACTOR = [0.85, 0.80, 0.90, 1.00, 1.25, 1.60, 1.45]  # Mon..Sun


def build() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    suppliers = SUPPLIERS
    ingredients = []
    by_name = {}
    for idx, (name, unit, cost, perishable, shelf, sup, margin) in enumerate(INGREDIENTS, start=1):
        ing_id = f"ING-{idx:03d}"
        by_name[name] = ing_id
        ingredients.append({
            "ingredient_id": ing_id,
            "name": name,
            "unit": unit,
            "unit_cost_paise": cost,
            "perishable": perishable,
            "shelf_life_days": shelf,
            "supplier_id": sup,
            "safety_margin_days": margin,
        })

    dishes, recipes = [], []
    for idx, (name, base, weekend, recipe) in enumerate(DISHES, start=1):
        dish_id = f"DISH-{idx:03d}"
        dishes.append({"dish_id": dish_id, "name": name, "active": True})
        for ing_name, qty in recipe.items():
            if ing_name not in by_name or qty <= 0:
                continue  # a recipe line referencing an unknown ingredient is dropped at seed time
            recipes.append({
                "recipe_id": f"REC-{len(recipes) + 1:04d}",
                "dish_id": dish_id,
                "ingredient_id": by_name[ing_name],
                "quantity_per_serving": round(qty, 5),
                "unit": next(i["unit"] for i in ingredients if i["ingredient_id"] == by_name[ing_name]),
            })

    # 12 weeks of daily sales ending yesterday, with day-of-week shape and a mild upward trend
    sales = []
    start = TODAY - timedelta(days=HISTORY_WEEKS * 7)
    for idx, (name, base, weekend, _recipe) in enumerate(DISHES, start=1):
        dish_id = f"DISH-{idx:03d}"
        for offset in range(HISTORY_WEEKS * 7):
            day = start + timedelta(days=offset)
            dow = day.weekday()
            factor = DOW_FACTOR[dow]
            if dow >= 4:
                factor *= weekend / 1.5
            trend = 1.0 + 0.11 * (offset / (HISTORY_WEEKS * 7))
            noise = RNG.uniform(0.86, 1.14)
            units = max(0, round(base * factor * trend * noise))
            sales.append({"dish_id": dish_id, "sale_date": day.isoformat(), "units_sold": units})

    # Current stock: deliberately a mix — some ingredients short, some over-bought and about to spoil
    stock = []
    for i, ing in enumerate(ingredients):
        # rough daily draw, used only to size an interesting opening position
        daily = sum(
            r["quantity_per_serving"] * DISHES[int(r["dish_id"][-3:]) - 1][1]
            for r in recipes if r["ingredient_id"] == ing["ingredient_id"]
        )
        if daily <= 0:
            daily = 0.05
        shelf = ing["shelf_life_days"] if ing["perishable"] else None
        if i % 5 == 0:
            # bought short: will run out inside the forward horizon
            days_cover = RNG.uniform(1.5, 3.5)
        elif i % 5 == 1:
            # over-bought: more than can be used before the use-by date, but a
            # quantity a real kitchen could plausibly have taken delivery of
            days_cover = RNG.uniform(1.6, 2.6) * shelf if shelf else RNG.uniform(20.0, 34.0)
        else:
            # comfortable: more than the forward horizon plus a supplier's lead
            # time, so these are not flagged at all. A perishable is still
            # capped by its own shelf life — you cannot hold 14 days of an
            # ingredient that keeps for three, which is why short-shelf-life
            # items legitimately stay on the list.
            days_cover = RNG.uniform(17.0, 30.0)
            if shelf:
                days_cover = min(days_cover, shelf * 0.9)
        qty = round(daily * days_cover, 3)
        entry = {"ingredient_id": ing["ingredient_id"], "quantity": qty,
                 "use_by_date": None, "snapshot_loaded_at": TODAY.isoformat()}
        if ing["perishable"]:
            shelf = ing["shelf_life_days"] or 5
            # received somewhere in the recent past, so the use-by sits across the horizon
            age = RNG.randint(0, max(1, shelf - 1))
            entry["use_by_date"] = (TODAY + timedelta(days=shelf - age)).isoformat()
        stock.append(entry)

    write("suppliers.json", suppliers)
    write("ingredients.json", ingredients)
    write("dishes.json", dishes)
    write("recipes.json", recipes)
    write("sales_history.json", sales)
    write("current_stock.json", stock)
    print(f"{len(dishes)} dishes, {len(ingredients)} ingredients, {len(suppliers)} suppliers, "
          f"{len(recipes)} recipe lines, {len(sales)} sales rows, {len(stock)} stock rows")


def write(name: str, payload: object) -> None:
    path = DATA / name
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(DATA.parent)}")


if __name__ == "__main__":
    build()
