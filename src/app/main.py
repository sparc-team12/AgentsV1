"""FastAPI application — the one deployable (ADR-001, modular monolith).

Every route but /api/v1/auth/login and the login page sits behind a session
check (REQ-043).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import auth, chat_agent, config, purchase_order, scenario
from .demand_engine import ingredient_demand
from .reference_data import dataset
from .risk_engine import assess_spoilage, assess_stockout, build_listing, rupees

app = FastAPI(
    title="Stocksense",
    version="1.0.0",
    description="PRD v1.6 (REQ-001 - REQ-044). Figures are computed deterministically and "
                "every one carries an arithmetic trace (REQ-028, REQ-029).",
)


# --- auth dependency (REQ-043) -----------------------------------------------


def current_user(request: Request) -> dict:
    user = auth.read_session(request.cookies.get(config.SESSION_COOKIE))
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return user


Auth = Depends(current_user)


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/v1/auth/login", tags=["auth"])
def login(body: LoginRequest, response: Response) -> dict:
    user = auth.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="That email and password do not match an account")
    response.set_cookie(
        config.SESSION_COOKIE, auth.issue_session(user),
        httponly=True, samesite="lax", path="/",
    )  # no max-age: OQ-8 resolved to no idle timeout in v1
    return {"user": user}


@app.post("/api/v1/auth/logout", tags=["auth"])
def logout(response: Response) -> dict:
    response.delete_cookie(config.SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/v1/auth/me", tags=["auth"])
def me(user: dict = Auth) -> dict:
    return {"user": user}


# --- data setup (REQ-037 - REQ-041) ------------------------------------------


@app.get("/api/v1/setup/status", tags=["data-setup"])
def setup_status(user: dict = Auth) -> dict:
    ds = dataset()
    return {
        "categories": ds.load_status(),
        "gaps": [{"category": g.category, "entity_id": g.entity_id, "detail": g.detail} for g in ds.gaps],
        "fully_loaded": all(c["loaded"] for c in ds.load_status()),
    }


@app.get("/api/v1/setup/menu", tags=["data-setup"])
def setup_menu(user: dict = Auth) -> dict:
    ds = dataset()
    return {"dishes": [
        {
            "dish_id": d.dish_id, "name": d.name, "active": d.active,
            "recipe": [
                {"ingredient_id": r.ingredient_id,
                 "ingredient_name": ds.ingredient(r.ingredient_id).name if ds.ingredient(r.ingredient_id) else "UNKNOWN",
                 "quantity_per_serving": str(r.quantity_per_serving), "unit": r.unit,
                 "gap": None if ds.ingredient(r.ingredient_id) else "ingredient not in master data"}
                for r in sorted(ds.recipes, key=lambda x: x.recipe_id) if r.dish_id == d.dish_id
            ],
        }
        for d in sorted(ds.dishes, key=lambda x: x.dish_id)
    ]}


@app.get("/api/v1/setup/ingredients", tags=["data-setup"])
def setup_ingredients(user: dict = Auth) -> dict:
    ds = dataset()
    return {
        "ingredients": [
            {
                "ingredient_id": i.ingredient_id, "name": i.name, "unit": i.unit,
                "unit_cost": rupees(i.unit_cost_paise), "unit_cost_paise": i.unit_cost_paise,
                "perishable": i.perishable, "shelf_life_days": i.shelf_life_days,
                "supplier_id": i.supplier_id,
                "supplier_name": ds.supplier(i.supplier_id).name if ds.supplier(i.supplier_id) else None,
                "lead_time_days": ds.supplier(i.supplier_id).lead_time_days if ds.supplier(i.supplier_id) else None,
                "safety_margin_days": ds.safety_margin_days(i),
                "gap": None if ds.supplier(i.supplier_id) and ds.safety_margin_days(i) is not None
                       else "missing supplier or safety margin",
            }
            for i in sorted(ds.ingredients, key=lambda x: x.ingredient_id)
        ],
        "suppliers": [
            {"supplier_id": s.supplier_id, "name": s.name, "lead_time_days": s.lead_time_days,
             "safety_margin_days": s.safety_margin_days}
            for s in sorted(ds.suppliers, key=lambda x: x.supplier_id)
        ],
    }


@app.get("/api/v1/setup/stock", tags=["data-setup"])
def setup_stock(user: dict = Auth) -> dict:
    ds = dataset()
    return {"snapshot_loaded_at": next((s.snapshot_loaded_at for s in ds.stock if s.snapshot_loaded_at), None),
            "note": "This is the most recent loaded snapshot, not a live feed (US-027 AC-3).",
            "stock": [
                {
                    "ingredient_id": s.ingredient_id,
                    "ingredient_name": ds.ingredient(s.ingredient_id).name if ds.ingredient(s.ingredient_id) else "UNKNOWN",
                    "quantity": str(s.quantity),
                    "unit": ds.ingredient(s.ingredient_id).unit if ds.ingredient(s.ingredient_id) else "",
                    "use_by_date": s.use_by_date.isoformat() if s.use_by_date else None,
                    "gap": ("perishable with no use-by date"
                            if ds.ingredient(s.ingredient_id) and ds.ingredient(s.ingredient_id).perishable
                            and s.use_by_date is None else None),
                }
                for s in sorted(ds.stock, key=lambda x: x.ingredient_id)
            ]}


@app.get("/api/v1/setup/sales-history", tags=["data-setup"])
def setup_sales_history(user: dict = Auth) -> dict:
    ds = dataset()
    expected = 12 * 7
    rows = []
    for d in sorted(ds.dishes, key=lambda x: x.dish_id):
        history = ds.sales_for(d.dish_id)
        rows.append({
            "dish_id": d.dish_id, "name": d.name, "days": len(history),
            "first_date": history[0].sale_date.isoformat() if history else None,
            "last_date": history[-1].sale_date.isoformat() if history else None,
            "total_units": sum(h.units_sold for h in history),
            "gap": None if len(history) >= expected else f"{len(history)} days, expected {expected}",
            "daily": [{"on": h.sale_date.isoformat(), "units": h.units_sold} for h in history],
        })
    return {"expected_days": expected, "dishes": rows}


# --- risk dashboard (REQ-023 - REQ-027) --------------------------------------


@app.get("/api/v1/risks", tags=["dashboard"])
def risks(user: dict = Auth) -> dict:
    listing = build_listing()
    return _serialise_listing(listing)


@app.get("/api/v1/risks/{ingredient_id}", tags=["dashboard"])
def risk_detail(ingredient_id: str, user: dict = Auth) -> dict:
    ds = dataset()
    ing = ds.ingredient(ingredient_id)
    if ing is None:
        raise HTTPException(status_code=404, detail="Unknown ingredient")
    as_of = config.today()
    horizon = config.horizon_days()
    demand = ingredient_demand(ingredient_id, as_of, horizon)
    stockout = assess_stockout(ingredient_id, demand, as_of)
    spoilage = assess_spoilage(ingredient_id, demand, as_of, config.materiality_threshold_paise())
    stock = ds.stock_for(ingredient_id)

    return {
        "ingredient": {
            "ingredient_id": ing.ingredient_id, "name": ing.name, "unit": ing.unit,
            "unit_cost": rupees(ing.unit_cost_paise), "perishable": ing.perishable,
            "shelf_life_days": ing.shelf_life_days,
            "supplier_name": ds.supplier(ing.supplier_id).name if ds.supplier(ing.supplier_id) else None,
            "lead_time_days": ds.supplier(ing.supplier_id).lead_time_days if ds.supplier(ing.supplier_id) else None,
            "safety_margin_days": ds.safety_margin_days(ing),
            "quantity_on_hand": str(stock.quantity) if stock else None,
            "use_by_date": stock.use_by_date.isoformat() if stock and stock.use_by_date else None,
        },
        "demand": {
            "total": str(demand.total),
            "daily": [{"on": d.on.isoformat(), "quantity": str(d.quantity)} for d in demand.daily],
            "contributions": [c.model_dump(mode="json") for c in demand.contributions],
            "trace": [t.model_dump() for t in demand.trace],
        },
        "stockout": _dump(stockout),
        "spoilage": (_dump(spoilage) | {"waste_cost": rupees(spoilage.waste_cost_paise)}
                     if spoilage else None),
    }


class ThresholdRequest(BaseModel):
    materiality_threshold_paise: int = Field(ge=0)


@app.put("/api/v1/config/materiality-threshold", tags=["dashboard"])
def set_threshold(body: ThresholdRequest, user: dict = Auth) -> dict:
    # REQ-012 — adjustable by the kitchen manager, no redeploy
    config.set_materiality_threshold_paise(body.materiality_threshold_paise)
    return _serialise_listing(build_listing())


# --- chat agent (REQ-013 - REQ-020, REQ-036) ---------------------------------


class ChatRequest(BaseModel):
    question: str
    ingredient_id: str | None = None


@app.post("/api/v1/chat", tags=["chat-agent"])
def chat(body: ChatRequest, user: dict = Auth) -> dict:
    # REQ-036 — one surface for explanation and what-if; the caller does not choose
    result = chat_agent.answer(body.question, body.ingredient_id)
    return _jsonable(result)


class ScenarioRequest(BaseModel):
    dish_id: str
    extra_servings: Decimal
    date_from: date
    date_to: date


@app.post("/api/v1/scenario/preview", tags=["chat-agent"])
def scenario_preview(body: ScenarioRequest, user: dict = Auth) -> dict:
    ds = dataset()
    dish = ds.dish(body.dish_id)
    if dish is None:
        raise HTTPException(status_code=404, detail="Unknown dish")
    result = scenario.preview(dish.dish_id, dish.name, body.extra_servings, body.date_from, body.date_to)
    return _jsonable(result)


# --- purchase orders (REQ-021, REQ-022) --------------------------------------


@app.post("/api/v1/purchase-orders/draft", tags=["purchase-orders"])
def po_draft(ingredient_id: str, user: dict = Auth) -> dict:
    result = purchase_order.draft(ingredient_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# --- serialisation helpers ---------------------------------------------------


def _serialise_listing(listing) -> dict:
    return {
        "as_of": listing.as_of.isoformat(),
        "horizon_days": listing.horizon_days,
        "total_waste_exposure": rupees(listing.total_waste_exposure_paise),
        "total_waste_exposure_paise": listing.total_waste_exposure_paise,
        "suppressed_count": listing.suppressed_count,
        "materiality_threshold": rupees(listing.materiality_threshold_paise),
        "materiality_threshold_paise": listing.materiality_threshold_paise,
        "data_gaps": listing.data_gaps,
        "rows": [
            {
                "ingredient_id": r.ingredient_id,
                "ingredient_name": r.ingredient_name,
                "risk_type": r.risk_type,
                "severity": r.severity_label,
                "order_by_date": r.order_by_date.isoformat() if r.order_by_date else None,
                "days_until_order_by": r.days_until_order_by,
                "waste_cost": rupees(r.waste_cost_paise) if r.waste_cost_paise is not None else None,
                "waste_cost_paise": r.waste_cost_paise,
                "unit": r.unit,
            }
            for r in listing.rows
        ],
    }


def _dump(model) -> dict | None:
    return model.model_dump(mode="json") if model is not None else None


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        if "rows" in value and hasattr(value, "get") and hasattr(value.get("rows"), "__iter__") \
                and "total_waste_exposure_paise" in value:
            return _serialise_listing(value)
        return {k: (_serialise_listing(v) if k == "listing" else _jsonable(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, (Decimal, date)):
        return str(value)
    return value


# --- the browser client (comp-web-client) ------------------------------------


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(config.WEB_DIR / "index.html")


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"ok": True, "as_of": config.today().isoformat()}


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.mount("/static", StaticFiles(directory=str(config.WEB_DIR)), name="static")
