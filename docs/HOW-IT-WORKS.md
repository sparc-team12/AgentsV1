# How Stocksense Works

This is a walk-through of the running system: what it does, how a number gets
from raw data to the screen, and why the code is shaped the way it is. It
assumes no prior context beyond "it's a kitchen ingredient-forecasting app."

If you want the *requirements* (what it must do) or the *decisions* (why one
design was chosen over another), see the PRD and `architecture.md` referenced
throughout the code as `REQ-xxx` and `ADR-xxx`. This document is about
mechanism, not justification — though the two are hard to fully separate here,
because the mechanism *is* the safety design.

---

## 1. The one-sentence version

A kitchen or F&B manager logs in, sees a ranked list of ingredients about to
either **run out** (stockout) or **go to waste** (spoilage), can ask a chat box
"why?" or "what if I add a banquet?", and can draft a purchase order — all
computed from six fixed input files, deterministically, with every number
traceable back to the arithmetic that produced it.

---

## 2. The shape of the system

```
                          ┌─────────────────────────┐
   Browser (no build) ───▶│   FastAPI app (main.py)  │───▶  6 JSON data files
   index.html/app.js      │   one process, one file  │      (src/data/*.json)
                          └────────────┬─────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                         ▼
       demand_engine.py         risk_engine.py             chat_agent.py
       (projects demand)   (stockout + spoilage + rank) (routes + explains)
              │                        │                         │
              └───────────┬────────────┘                         │
                           ▼                                     │
                    reference_data.py  ◀────────────── scenario.py / purchase_order.py
                 (loads + validates the 6 files)         (what-if / PO draft, reuse the above)
```

It is a **modular monolith** (ADR-001): one FastAPI process, one deployable.
Locally it runs with `uvicorn`; in AWS it's the same ASGI app wrapped by
`Mangum` behind a single Lambda Function URL (`src/lambda_handler.py`,
`template.yaml`) with one DynamoDB table for the one piece of mutable state.
No API Gateway, no VPC, no database server, no queue — deliberately the
smallest surface that can serve this product.

**Why a monolith, not microservices?** There is one team, one deployable
concern, and the modules already have clean boundaries enforced by imports
alone (`chat_agent` never reaches into `risk_engine`'s internals; it calls
`assess_stockout`/`assess_spoilage` the same way `main.py` does). Splitting
this into services would add network calls and eventual-consistency risk to
buy an independence nobody needs yet.

---

## 3. The data model: six fixed inputs

Everything downstream derives from six JSON files loaded once at startup
(`reference_data.py`), matching the PRD's "Input Data" section exactly:

| File | Domain type | What it holds |
|---|---|---|
| `dishes.json` | `Dish` | menu items, active flag |
| `recipes.json` | `Recipe` | dish → ingredient → quantity per serving |
| `ingredients.json` | `Ingredient` | unit, cost, perishability, shelf life, supplier, safety margin |
| `suppliers.json` | `Supplier` | lead time, (fallback) safety margin |
| `current_stock.json` | `StockOnHand` | quantity on hand, use-by date |
| `sales_history.json` | `SalesRecord` | 12 weeks of daily units sold per dish |

These are Pydantic **frozen** models (`domain.py`) — once loaded, nothing
mutates them. The vocabulary here (`Dish`, `Severity`, `Order-by date`, `Waste
cost`, …) is taken verbatim from the PRD glossary; renaming a field here
without updating the PRD is treated as a real defect, not a refactor, because
every other module and every trace label depends on the name matching.

**Data gaps are surfaced, never silently patched.** On load, `_validate()`
checks for: a recipe pointing at an unknown ingredient, an ingredient with no
mapped supplier, a perishable ingredient with no use-by date, and an
ingredient (or its supplier) with no configured safety margin. Each becomes a
`Gap` shown on the "Data Setup" screen and folded into the risk listing's
`data_gaps`. The alternative — assuming a safety margin of 0, say — would
silently produce a number nobody asked for; the design would rather show
"missing" than guess.

---

## 4. Two numbers a manager actually cares about

Everything in the product exists to answer two questions per ingredient:
**will it run out**, and **will it go to waste**. Both start from the same
demand projection.

### 4.1 Demand projection (`demand_engine.py`)

For each *active* dish, for each of the next `horizon_days` (default 14), the
engine asks: "on this day of the week, how much of this dish do we usually
sell?" It looks at that weekday's history across the last 12 weeks and takes a
**recency-weighted mean** — a Saturday three weeks ago counts for `0.85³` as
much as last Saturday (`TREND_DECAY = 0.85`). This gives a demand curve per
dish that respects the fact that a restaurant's Friday looks nothing like its
Tuesday, and that a menu item trending up recently should be forecast to keep
trending up rather than being smoothed away by a flat 12-week average.

Dish demand is then pushed through the recipe table — "3 kg of Chicken Dum
Biryani needs 0.4 kg of Basmati Rice per serving" — and summed **across every
dish that uses that ingredient** to get one ingredient-level demand curve.
That's `ingredient_demand()`, and it's the one function everything else in the
product calls.

### 4.2 Stockout risk (`risk_engine.assess_stockout`)

Walk the projected daily demand forward from today, accumulating it against
current stock. The first day the running total exceeds stock on hand is the
**projected stockout date**. From there:

```
order-by date = stockout date − supplier lead time − safety margin
suggested order quantity = demand projected to occur between the stockout
                            date and (stockout date + lead time + margin)
```

If lead time or safety margin is missing, no order-by date is computed at
all — that's reported as a data gap, not defaulted to zero, because a
fabricated date is worse than an honest "can't tell you."

**Severity** is purely a function of how many days away the order-by date is:
`≤2 days → Critical`, `≤7 → High`, otherwise `Low`. Notably, an order-by date
that has already passed still falls in "≤2 days" and is Critical — there's no
separate "overdue" band, by design.

### 4.3 Spoilage risk (`risk_engine.assess_spoilage`)

Only applies to perishable ingredients with a use-by date. Sum the demand
projected to land on-or-before the use-by date; whatever's left over is
`unconsumed_quantity`, and `unconsumed_quantity × unit cost` is the **waste
cost**. Severity here is banded on the money, not the date: `≥₹2000 →
Critical`, `≥₹500 → High`, otherwise `Low`.

### 4.4 The dashboard's one rule that isn't obvious

Both risk types share one severity scale and are shown **interleaved** in a
single ranked list, not two separate tables — because a manager doesn't care
whether the ₹3,000 problem is a stockout or spoilage, only that it's the
worst thing on their plate today. Within a band, stockout rows sort by
proximity to their order-by date and spoilage rows by waste cost; the two
sorted sequences are then merged position-by-position, since the PRD doesn't
define a cross-type tiebreak and the code says so in a comment rather than
inventing an unstated rule quietly.

There's a second subtlety worth knowing: the **materiality threshold**
(default ₹500, adjustable live from the dashboard) hides small spoilage
warnings from the *list*, but the **total waste exposure figure always
includes them**. Raising the threshold to declutter the view can never make
the headline number look artificially better — it's structurally invariant
under that control, which is exactly what stops the threshold from becoming a
way to hide real cost.

---

## 5. Determinism and traceability aren't features, they're the architecture

Two rules run through every engine in this codebase, and both are enforced
structurally rather than by convention:

1. **"Today" is always an explicit parameter, never `date.today()` inside an
   engine.** `config.today()` reads `APP_TODAY` (fixed to `2026-09-18` for
   this dataset) so the same inputs always produce the same outputs — you can
   replay any day and get identical figures, which matters for testing and
   for trusting the numbers at all.
2. **No engine returns a bare number.** Every risk, every demand total, comes
   back as a value *plus* a `list[TraceStep]` — the literal arithmetic that
   produced it ("stockout date − 3d lead time − 2d safety margin = order-by
   date"). The dashboard's "How this was calculated" disclosure in the UI is
   just that trace rendered as a table. This isn't a UI nicety bolted on
   after the fact; the return type itself (`Traced[T]`) makes it impossible
   to add a new figure without also carrying its derivation.

All money is an integer count of **paise** (never a float — `ADR-008`), and
all quantities are `Decimal`. This matters more than it sounds: floats would
silently drift after enough addition, and a kitchen manager acting on a
drifted ₹ figure is a much worse failure than a slow test suite.

---

## 6. The chat agent — and the one design decision that matters most

`chat_agent.py` is the most interesting file in the codebase, because it
looks like an AI feature but is architected to behave like a very literal
calculator with a friendly voice.

**It has to serve two intents through one text box** (REQ-036 — the manager
never picks a mode): "why is Prawns flagged?" (explain) and "what if we add a
50-cover banquet of Biryani on Saturday?" (what-if). Routing between them is
a deliberately dumb keyword/regex classifier — markers like `"why"`,
`"explain"` route to explanation; `"what if"`, `"banquet"`, `"add "` plus a
matched dish name route to what-if. No model call, no ambiguity to debug,
and — critically — **nothing here can hallucinate an intent** because there's
no generative step in the decision at all.

### 6.1 Explaining a flag

`_explain()` doesn't reason about *why* something is at risk — it just calls
`ingredient_demand()`, `assess_stockout()`, `assess_spoilage()` (the exact
same functions the dashboard calls) and **reads the answer out of their
output**. The prose is built by string-formatting the already-computed
figures: "Prawns is drawn by 4 dishes... exhausts stock on 2026-09-25...
Seafood Co. takes 3 days to deliver... order-by is 2026-09-20."

### 6.2 What-if scenarios

`scenario.py` builds a demand **overlay** — the extra covers spread evenly
across the stated date range — and re-runs `build_listing()` twice: once
against the real baseline, once with the overlay merged in. The answer is a
**diff**: which ingredients newly became at-risk, which order-by dates moved
and by how much, how total waste exposure changed. Nothing is ever written to
storage — a what-if is a pure, throwaway recomputation (`ADR-011`); reloading
the page discards it and the real dashboard reappears. This is also why the
feature is safe to let a manager play with freely: there's no "undo," because
there's nothing to undo.

### 6.3 The one rule the whole feature exists to prove

> **The language layer never computes a number.** (`ADR-006`)

This is stated explicitly in the module docstring and it's the answer to "how
do you stop the chatbot from making things up." Every figure in a chat answer
was computed by `demand_engine`/`risk_engine` *before* any text is generated;
the LLM step (`_phrase()`), if enabled at all, is handed the finished prose
**and the exact set of figures used**, and is only allowed to reword it. A
regex check (`_numbers_within`) scans the model's output afterward and
rejects it — silently falling back to the deterministic text — if it contains
even one number, date, or amount not in the original figure set. So worst
case, the LLM's output is discarded and the safe, boring, guaranteed-correct
sentence ships instead. That fallback is the whole point: a wrong number
shown to someone deciding what to order is a real financial mistake, not a
UX blemish, so the system is built to fail safe rather than fail smooth.

By default this LLM rewording pass is **off** (`PHRASING_BACKEND` unset); when
turned on it currently targets Amazon Bedrock. That backend is swappable —
Google AI Studio, for instance, could serve the identical narrow role (reword
only, verified after the fact) with no change to the safety guarantee, since
the guarantee lives in `_numbers_within()`, not in which model is called.

---

## 7. Request lifecycle, end to end

Walking through "why is Prawns flagged?" from click to screen:

1. **Browser** (`app.js`) — no framework, no build step, plain DOM — posts
   `{"question": "...", "ingredient_id": null}` to `/api/v1/chat`.
2. **`main.py`** checks the session cookie (`current_user`), calls
   `chat_agent.answer(...)`, and serialises whatever comes back
   (`_jsonable`) — Decimals and dates become strings, nested `listing`
   objects get the same shape the `/risks` endpoint returns, so the frontend
   has one code path for rendering a listing regardless of who produced it.
3. **`chat_agent.answer()`** classifies the intent, calls `_explain()`.
4. **`_explain()`** calls `dataset()` (cached, in-memory, already validated),
   `ingredient_demand()`, `assess_stockout()`, `assess_spoilage()` — the exact
   same call chain `GET /api/v1/risks/{id}` makes for the detail panel.
5. Figures are formatted into prose and a `figures` list; optionally passed
   through the guarded LLM rewording step.
6. **Response** carries `{intent, answer, figures, trace, contributions}`;
   the browser renders the prose, a row of figure chips, and (for what-if) a
   note that the dashboard above is now showing the scenario-adjusted,
   throwaway view.

The dashboard's own load (`GET /api/v1/risks`) is the same shape without the
chat wrapper: `build_listing()` → `assess_all()` → `ingredient_demand()` for
every ingredient, ranked, summed, returned.

---

## 8. Auth, sessions, and what's deliberately *not* here

Two named personas — `kitchen-manager` and `fb-manager` — with **identical
access**; there's no role column because the product's open questions were
resolved to "both personas see the same thing" (`OQ-9`). Login produces a
signed, stateless cookie (`HMAC-SHA256` over a base64 payload) — no server-
side session store needed, no database round-trip on every request. Passwords
are hashed with PBKDF2 (240,000 rounds) rather than Argon2, which was the
architecture's stated preference — Argon2 needs a compiled wheel, and keeping
the Lambda a dependency-light zip won out. That trade-off is recorded as a
known deviation in the code, not hidden.

Two things are **deliberately absent**, both by resolved open question rather
than oversight: session idle timeout (the cookie never expires) and any
procurement integration (the purchase-order draft is text you copy out
yourself — REQ-022 explicitly excludes ever sending it anywhere). Knowing
what a system *chose* not to do is as load-bearing as knowing what it does.

---

## 9. Configuration as data, not code

The materiality threshold (default ₹500) and forecast horizon (default 14
days) live in a tiny key-value store (`config.py`), not in source — because
`REQ-012` requires the threshold be changeable by a manager without a
redeploy. Locally that store is a JSON file; on AWS it's one DynamoDB table
with pay-per-request billing. Same interface, two backends, chosen by whether
`TABLE_NAME` is set in the environment — so local development needs nothing
installed, and production needs no database server to manage.

---

## 10. Where to look next

- **Add a new kind of risk?** Start in `domain.py` (define the shape), then
  `risk_engine.py` (compute it, with a `TraceStep` for every figure).
- **Change how demand is projected?** `demand_engine.project_dish_demand()` is
  the one function that owns the weighting/decay logic.
- **Understand a specific number on screen?** Click "How this was calculated"
  on the dashboard — it's reading the same `trace` list this document
  describes, not a summary of it.
- **Wire in a different LLM for chat phrasing?** Everything you need is
  scoped to `chat_agent._phrase()` and `_numbers_within()`; nothing else in
  the codebase needs to change or know it happened.
