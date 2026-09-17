# Architecture: Ingredient Demand Forecasting Assistant

**Version:** 1.2 | **Status:** Draft — awaiting approval | **Last Updated:** 2026-09-18
**Designed against:** `docs/01-prd/prd-ingredient-demand-forecasting.md` @ **v1.6 (Confirmed)**
**Backlog:** `docs/02-stories/backlog-draft.md` + `docs/02-stories/story-index.md` @ PRD v1.6 sync — 30 stories (US-001–US-030), 8 areas
**Journeys:** `docs/01b-user-journey/journeys.md` @ v1.0
**Instance:** `PROJECT.md` — project `ACRI`, `cloud_provider` recorded as `none`, `aws_region: us-east-1`, `aws_account_id: 092338124082`

> **Source-reading note for this run.** Jira and Confluence were **not** queried. Per explicit instruction, this design was derived from the local repository documents only, using `docs/02-stories/story-index.md` as the backlog view. That index is a **cache, not the source of truth** — if Jira has drifted since the 2026-09-17 sync, this design's story assignments drift with it. The `comp-*` write-back to Jira has **not** been performed and remains outstanding (§15).

---

## 1. Summary

A **modular monolith**: one Python **FastAPI** service on AWS App Runner, one Postgres database, one React (TypeScript) single-page app on S3/CloudFront, deployed by GitHub Actions. The eight modules below are **code and ownership boundaries inside that one deployable**, not separate services — seven of them are Python packages in the service, one is the browser client.

The single most important structural decision is the split between **computation and language** (ADR-006): every rupee figure and every date is produced by a deterministic arithmetic engine and carries a machine-readable trace; the LLM behind the Chat Agent receives those already-computed figures and is permitted only to put them into sentences. It is never given raw inputs and asked to do arithmetic. REQ-028, REQ-029, REQ-030 and REQ-031 all collapse onto this one rule, and the product's own acceptance criteria (Success Metrics steps 3 and 5) fail the moment it is violated.

---

## 2. Constraint check before anything else

The PRD's Constraints section is binding. Read against it:

| Constraint (PRD) | How this design respects it |
|---|---|
| Fixed-deadline build; scope is a ceiling | Modular monolith, one datastore, one always-warm service. No microservices, no service mesh, no event bus, no Kubernetes. Every module boundary is a folder and an interface, not a deployment. |
| Desktop or tablet browser only | Responsive React SPA. No native shell, no mobile-specific interface, no offline mode. |
| Per-user login for two personas, no further roles | A `users` table with exactly two rows and no role column (ADR-010). No authorisation layer is built, because OQ-9 resolved to identical access. |
| Data is supplied, not sourced | No POS connector, no supplier portal client. The only ingress is the five Data Setup screens (REQ-037–041). |
| Units guaranteed consistent | No conversion module exists. Unit is a display string carried alongside a quantity, never interpreted. |
| Currency is INR throughout | All money is a single `Paise` integer type (ADR-008). No multi-currency abstraction. |
| Supplier lead times fixed | `lead_time_days` is a plain integer column. No distribution, no variance model. |

Nothing in the PRD's Constraints rules out any choice below, and no choice below requires budget or timeline the Constraints do not allow.

---

## 3. The NFR gate

The PRD's **Non-Functional** bucket is **populated** (REQ-028 – REQ-035), so this design is **not** blocked in the way the NFR gate contemplates. Determinism, traceability, LLM-figure discipline, cross-surface consistency, relative latency, non-colour severity encoding and INR denomination are all stated requirements and all are designed for in §8.

Six inputs a stack decision would normally want are nonetheless **absent from the PRD**. None of them blocks a decision here, because the product's own numbers make the answer insensitive — a single kitchen, two named users, 15–20 dishes, 30–40 ingredients, a 14-day horizon and 12 weeks of history is a dataset measured in kilobytes. Each is therefore recorded as an **assumption**, not invented as a requirement, and each is returned to agent 01 in §12.

| # | Missing NFR | Assumption made | Cost if wrong |
|---|---|---|---|
| A-1 | Concurrency / expected load | ≤ 2 concurrent users, < 100 requests/day | None at this scale. One App Runner instance at 1 vCPU absorbs two orders of magnitude more. |
| A-2 | Quantified latency for REQ-032 / REQ-033 | Dashboard p95 < 800 ms; Chat Agent first token < 2 s, complete < 6 s | Low. Drives the always-warm hosting choice (ADR-003) and response streaming — both the cheap option anyway. |
| A-3 | Accessibility standard | WCAG 2.1 AA as a working target; REQ-034 is the only contractual part | Low–moderate. A formal AA audit obligation discovered late costs frontend rework in `comp-web-client`. |
| A-4 | Browser / device matrix | Current Chrome, Edge, Safari and iPadOS Safari; ≥ 1024 px viewport | Low. Legacy-browser support would change a build target in `comp-web-client` only. |
| A-5 | Data retention, backup, RPO/RTO | 7-day automated RDS snapshot retention, no archival obligation | Low–moderate. A stated RPO/RTO changes the database tier, not the design. |
| A-6 | Credential-handling obligation | Passwords are the only secret; Argon2id hashing; no password policy stated | Moderate. The PRD's "no compliance controls" line predates the login. |

**Note on A-6.** The PRD's Non-Goals still read *"Compliance controls — no personal, customer or payment data is involved."* That was true at v1.3. Since v1.4 the system stores two people's email addresses and password hashes. This does not change the design, but it is a stale sentence in a Confirmed PRD and belongs back with agent 01.

---

## 4. Modules

`area-*` slugs were the starting hypothesis. Boundaries below are drawn from **data ownership** and **rate of change**.

| `comp-` slug | Responsibility (one line) | Data it owns | Covers `area-*` |
|---|---|---|---|
| `comp-reference-data` | Loads, validates and serves the six supplied input datasets, and owns the canonical domain types every other module imports | Dish, Recipe, Ingredient, Supplier, StockOnHand, SalesHistory, Configuration | `area-data-setup` |
| `comp-auth` | Authenticates a persona and establishes a session; gates every screen | User, Session | `area-auth` |
| `comp-demand-engine` | Projects dish demand from sales history and maps it through recipes to ingredient demand | DemandProjection (derived) | `area-demand-projection` |
| `comp-risk-engine` | Assesses stockout and spoilage risk, assigns the shared severity scale, computes order-by date, order quantity, waste cost, materiality suppression, aggregate exposure and the combined dashboard ranking | StockoutRisk, SpoilageRisk, RiskListing (all derived) | `area-stockout-risk`, `area-spoilage-risk` |
| `comp-scenario` | Applies a what-if demand overlay, re-runs demand + risk deterministically, and diffs against the baseline | ScenarioOverlay (transient, never persisted) | `area-chat-agent` (what-if half) |
| `comp-chat-agent` | Parses a natural-language question or scenario into a typed intent, and renders already-computed figures into prose | ConversationTurn (transient) | `area-chat-agent` (explanation half) |
| `comp-purchase-order` | Produces the editable purchase-order draft text for a stockout-risk ingredient | PurchaseOrderDraft (per session) | `area-purchase-orders` |
| `comp-web-client` | The browser application — every screen the two personas see | Client-side view state only | `area-dashboard`; the screen half of `area-data-setup`, `area-purchase-orders`, `area-auth` |

### 4.1 Why these, and not the eight areas one-for-one

- **`area-stockout-risk` + `area-spoilage-risk` → one `comp-risk-engine` (merge).** The PRD Glossary defines **Severity** as *one* shared three-band scale across both risk types, and REQ-023 requires them **interleaved** in a single ranked list where a Critical spoilage item outranks a High stockout item. Splitting them would leave the cross-type ranking rule in neither module, or duplicate the severity scale in both. They read the same two inputs (projection, stock), change at the same rate, and could only ever deploy together.
- **`area-chat-agent` → `comp-chat-agent` + `comp-scenario` (split).** These have opposite correctness properties. `comp-scenario` is deterministic arithmetic and must satisfy REQ-028; `comp-chat-agent` is LLM-driven and must satisfy REQ-030 by never doing arithmetic at all. Keeping them in one module is what makes REQ-030 easy to violate by accident. This split is the enforcement mechanism for ADR-006.
- **`comp-reference-data` also owns the canonical types.** A separate shared-types module would carry no stories and no behaviour. The domain vocabulary is defined where the data lives.
- **No `comp-platform`.** Infrastructure, CI and observability are described in §9. They own no story and no data, so minting a slug for them would produce a label nothing could wear.
- **No separate trace module.** Rather than a cross-cutting provenance service labelled onto a third of the backlog, **each engine emits its own trace alongside every figure it returns** (ADR-009). REQ-029 is a property of the return type, not a component.

### 4.2 `area-* → comp-*` map

Every area resolves. A change request arriving labelled by area has a deterministic module.

| `area-*` | Primary `comp-*` | Also touches |
|---|---|---|
| `area-auth` | `comp-auth` | `comp-web-client` (login screen) |
| `area-data-setup` | `comp-reference-data` | `comp-web-client` (the five setup screens) |
| `area-demand-projection` | `comp-demand-engine` | — |
| `area-stockout-risk` | `comp-risk-engine` | — |
| `area-spoilage-risk` | `comp-risk-engine` | — |
| `area-chat-agent` | `comp-chat-agent` | `comp-scenario` (what-if stories) |
| `area-purchase-orders` | `comp-purchase-order` | `comp-web-client` |
| `area-dashboard` | `comp-web-client` | `comp-risk-engine` (ordering REQ-023, aggregate REQ-027) |

---

## 5. Stack

| Layer | Choice | Driven by | Rejected |
|---|---|---|---|
| Backend language / framework | **Python 3.12 + FastAPI**, Pydantic v2 models, SQLAlchemy 2.0, uvicorn | Stated platform requirement; Python 3.12.10 verified present in `PROJECT.md`; Pydantic gives REQ-029's `{value, trace}` shape as a typed model and REQ-028's exact arithmetic via `Decimal`/`int` | Flask/Django (no first-class typed response models or generated OpenAPI); Node/TypeScript backend |
| Frontend language | **TypeScript + React 18 + Vite** | Type safety across the API boundary; Node 22.23.2 verified present in `PROJECT.md` | Server-rendered Python templates — the dashboard and Chat Agent are interactive surfaces (REQ-018–020, REQ-033) |
| API contract | **OpenAPI 3.1 emitted by FastAPI**, TypeScript client generated from it in CI | REQ-031 — the two languages must not drift on any figure's shape or name (ADR-002) | Hand-written client types (drift is invisible until a figure disagrees, which is the exact REQ-031 failure) |
| API service | **AWS App Runner**, container from ECR (uvicorn behind the platform's proxy) | REQ-032 (always warm, no cold start); fixed-deadline Constraint; `PROJECT.md` already names App Runner as the intended target | Lambda + API Gateway (cold start works against REQ-032, and a Python image plus VPC attachment and RDS Proxy is more moving parts than the rest of this design); ECS/Fargate (more Terraform for the same property); EC2 (patching) |
| Database | **Amazon RDS for PostgreSQL 16**, `db.t4g.micro`, single-AZ | REQ-004 (the recipe/dish/ingredient aggregation is a join), REQ-029 (traces are rows), REQ-007/REQ-012 (configuration is data) | DynamoDB (single-table modelling of a three-way join buys nothing at 40 ingredients); Aurora Serverless v2 (ACU floor exceeds t4g.micro at this scale); JSON in S3 loaded at boot (no home for credentials or editable configuration) |
| Frontend | **React 18 + Vite**, static SPA on **S3 + CloudFront** | Desktop/tablet Constraint, REQ-032, REQ-034 | Server-side rendering (no SEO and no first-paint requirement to pay for it) |
| LLM | **Amazon Bedrock**, Claude model family, streaming via `boto3` | REQ-013, REQ-017, REQ-033; keeps the only external dependency inside the existing AWS account | A direct third-party API (a second vendor, a second credential path, egress out of the account, for no capability this design uses) |
| Auth | **In-application email + Argon2id** (`argon2-cffi`), HttpOnly signed session cookie | REQ-043, REQ-044; OQ-6/7/8 resolved to *no* MFA, *no* self-service reset, *no* idle timeout | Amazon Cognito — its value is exactly the three features the client removed |
| IaC | **Terraform** | Reviewability at the approval gate — the plan is the artifact a human approves | CDK (one-language consistency is real, but a reviewable plan matters more here); console changes (not reproducible) |
| CI/CD | **GitHub Actions**, OIDC role assumption into account `092338124082` | Stated delivery platform for this build | Long-lived IAM access keys in repository secrets |
| Money | **Integer paise** — Python `int`, Postgres `BIGINT`; quantities in `Decimal` with an explicit scale; formatted to INR at the render edge | REQ-011, REQ-027, REQ-028, REQ-035 | `float` — two runs summing the aggregate in different orders can differ in the last paisa, breaking REQ-028 and REQ-031 |

---

## 6. Data model

Entity names are taken **verbatim from the PRD Glossary**. Vocabulary drift here breaks every downstream search.

| Entity | Key fields | Owned by |
|---|---|---|
| **Dish** | `dish_id`, `name`, `active` | `comp-reference-data` |
| **Recipe** | `recipe_id`, `dish_id` → Dish, `ingredient_id` → Ingredient, `quantity_per_serving`, `unit` | `comp-reference-data` |
| **Ingredient** | `ingredient_id`, `name`, `unit`, `unit_cost_paise`, `perishable`, `shelf_life_days`, `supplier_id` → Supplier, `safety_margin_days` (nullable) | `comp-reference-data` |
| **Supplier** | `supplier_id`, `name`, `lead_time_days`, `safety_margin_days` (nullable) | `comp-reference-data` |
| **StockOnHand** | `ingredient_id` → Ingredient, `quantity`, `use_by_date`, `snapshot_loaded_at` | `comp-reference-data` |
| **SalesHistory** | `dish_id` → Dish, `sale_date`, `units_sold` | `comp-reference-data` |
| **Configuration** | `key`, `value`, `updated_at` — holds `materiality_threshold_paise` (seeded 50000 = ₹500) and `forward_horizon_days` (seeded 14) | `comp-reference-data` |
| **User** | `user_id`, `email`, `password_hash`, `persona` (`kitchen-manager` \| `fb-manager`) | `comp-auth` |
| **Session** | `session_id`, `user_id` → User, `issued_at` — **no expiry column** (OQ-8: no idle timeout in v1) | `comp-auth` |
| **DemandProjection** | `dish_id` or `ingredient_id`, `projection_date`, `projected_quantity`, `trace` | `comp-demand-engine` (derived) |
| **StockoutRisk** | `ingredient_id`, `projected_stockout_date`, `order_by_date`, `suggested_order_quantity`, `severity`, `trace` | `comp-risk-engine` (derived) |
| **SpoilageRisk** | `ingredient_id`, `unconsumed_quantity`, `waste_cost_paise`, `use_by_date`, `severity`, `suppressed`, `trace` | `comp-risk-engine` (derived) |
| **ScenarioOverlay** | `dish_id`, `delta_servings`, `date_from`, `date_to` — **in-memory only, never written** | `comp-scenario` |
| **PurchaseOrderDraft** | `ingredient_id`, `supplier_name`, `item`, `quantity`, `required_delivery_date`, `body_text`, `edited` | `comp-purchase-order` |

**Safety-margin resolution (REQ-007, REQ-039).** The margin is looked up **ingredient first, then supplier**. If neither carries a value, the order-by date is **not computed** and the ingredient surfaces as a data gap — never silently defaulted to zero. This is the explicit requirement of US-004 AC-3 and US-026 AC-5.

**Derived data.** `DemandProjection`, `StockoutRisk` and `SpoilageRisk` are persisted only as a cache keyed by an input-data fingerprint. They are fully recomputable from inputs at any time, which is what makes REQ-028 checkable: recompute and compare.

---

## 7. API surface

One HTTP API, `/api/v1`, JSON. Every route except `/auth/login` requires a valid session cookie (REQ-043).

| Method + path | Returns | Module | Requirements |
|---|---|---|---|
| `POST /auth/login` | session cookie, persona | `comp-auth` | REQ-043, REQ-044 |
| `POST /auth/logout` | 204 | `comp-auth` | REQ-043 |
| `GET /setup/status` | per-category load status for the hub | `comp-reference-data` | REQ-037 |
| `POST /setup/{menu\|ingredients\|stock\|sales-history}` | load result + validation gaps | `comp-reference-data` | REQ-038–041 |
| `GET /setup/{menu\|ingredients\|stock\|sales-history}` | the loaded dataset + flagged gaps | `comp-reference-data` | REQ-038–041 |
| `GET /risks` | ranked risk listing + `total_waste_exposure_paise` | `comp-risk-engine` | REQ-023–027, REQ-034, REQ-035 |
| `GET /risks/{ingredientId}` | full detail, both risk types, with traces | `comp-risk-engine` | REQ-006–011, REQ-029, REQ-042 |
| `GET /projection/{ingredientId}` | day-by-day projection + per-dish contributions | `comp-demand-engine` | REQ-001–004, REQ-014 |
| `PUT /config/materiality-threshold` | new threshold, recomputed listing | `comp-reference-data` | REQ-012 |
| `POST /chat` (streaming) | typed intent + prose answer + the `figure_refs` it cited | `comp-chat-agent` | REQ-013–017, REQ-033, REQ-036 |
| `POST /scenario/preview` | newly at-risk, order-by deltas, exposure delta | `comp-scenario` | REQ-018–020 |
| `POST /purchase-orders/draft` | editable draft text | `comp-purchase-order` | REQ-021, REQ-022 |

**`/chat` is one endpoint, not two** — REQ-036 requires explanation and what-if to share a surface. The intent classifier inside `comp-chat-agent` routes to `comp-risk-engine` (explain) or `comp-scenario` (what-if); the caller does not choose.

**Every figure-bearing response carries a `trace`** — an ordered list of `{operand, value, source}` steps terminating in input-data rows (REQ-029). The Chat Agent is given *only* these objects, never raw inputs.

---

## 8. Non-functional strategy

| REQ | How it is met |
|---|---|
| **REQ-028** determinism | Pure functions over frozen Pydantic snapshot models. Integer paise and `Decimal` quantities, no `float` in any published figure (ADR-008). Explicit `sorted()` by id before any summation — dict iteration order must never decide a total. "Today" is an explicit parameter passed in at the API edge, never `date.today()` inside an engine; otherwise the same inputs give different answers on different days and the requirement is untestable. A Hypothesis property test recomputes a full run twice and asserts equality. |
| **REQ-029** traceability | Engines return `Traced[T]` — `{value, trace}` — never a bare number (ADR-009). `GET /risks/{id}` exposes the trace; it is also what `comp-chat-agent` consumes. |
| **REQ-030** LLM never estimates | ADR-006. The Bedrock prompt contains only pre-computed `{label, value, unit, source}` tuples and an instruction to use them verbatim. A post-response validator extracts every numeral from the generated text and rejects the turn if any numeral is absent from the supplied set. |
| **REQ-031** consistency | The dashboard and the Chat Agent read the **same** cached risk rows for the same input fingerprint. There is no second code path that could disagree. |
| **REQ-032** dashboard fast | `GET /risks` serves the cached listing; recomputation happens on data load, not on read. App Runner stays warm, so there is no cold start. Target p95 < 800 ms (assumption A-2). |
| **REQ-033** chat within seconds | Bedrock streaming returned as a FastAPI `StreamingResponse`, so the first token arrives well inside the budget. The arithmetic is already finished before the model is called. |
| **REQ-034** severity legible without colour | `comp-web-client` renders the literal strings `Critical` / `High` / `Low` as text in every severity position, with colour as a secondary encoding only. Enforced by a component test asserting the text node exists. |
| **REQ-035** INR | `Paise` integer end to end; formatted with the `en-IN` locale at the render edge only. |
| **REQ-043 / REQ-044** auth | One FastAPI dependency guards every route but `/auth/login`. Two seeded users, distinct credentials, identical access (OQ-9). |

---

## 9. Deployment and integration

```
GitHub (main)
  └── GitHub Actions ── OIDC ──> AWS account 092338124082 (us-east-1)
        ├── python: ruff + mypy + pytest (+ Hypothesis determinism check)
        ├── contract: regenerate the TS client from FastAPI's OpenAPI schema,
        │             fail the build if it differs from the committed one (ADR-002)
        ├── web: eslint + tsc + vitest
        ├── docker build (python:3.12-slim + uvicorn) ──> ECR ──> App Runner
        ├── vite build ──> S3 ──> CloudFront invalidation   [comp-web-client]
        ├── alembic upgrade head (migrations, gated on prod)
        └── terraform plan (posted to the PR) / terraform apply (gated)

  CloudFront ──> S3 (SPA)
  App Runner ──> RDS PostgreSQL (private subnet, security-group restricted)
             ──> Amazon Bedrock (Claude, streaming, via boto3)
             ──> Secrets Manager (DB credentials, session signing key)
```

**Integration points.** Exactly one external service: **Amazon Bedrock**, required by REQ-013 and REQ-017. The provider is decided; the model id is configuration, not code. There is no payment gateway, no courier and no supplier portal — the PRD's Non-Goals exclude all procurement integration, so no vendor decision is outstanding.

**Environments.** `dev` and `prod`, same Terraform module, different tfvars. `terraform apply` against `prod` is a hard gate per `CONVENTIONS.md` §6.

**Region.** `us-east-1`, taken from `PROJECT.md`. See ADR-013 — questioned, not settled.

---

## 10. Module build order

**This is a live input to work selection.** `CONVENTIONS.md` §5 tier 3 ranks Ready stories by a module's position in this list, so **approving this section approves a build sequence**. Ordered by **dependency**, not importance. The graph is acyclic.

1. **`comp-reference-data`** — owns the canonical domain types and all six input datasets. Every other module imports its types; nothing can be computed before data can be loaded. Depends on nothing.
2. **`comp-auth`** — gates every screen (REQ-043), so every other module's routes sit behind it. Depends only on the domain types.
3. **`comp-web-client`** — depends on the published API contracts and on `comp-auth`, not on any engine's implementation. Third because the five Data Setup screens are the only way data enters the system: until they exist, nothing downstream has anything to run against.
4. **`comp-demand-engine`** — reads recipes, dishes and sales history from `comp-reference-data`. Every risk figure stands on its output.
5. **`comp-risk-engine`** — consumes the demand projection plus stock, ingredients and suppliers. The dashboard, the purchase order, the scenario diff and the Chat Agent all read its figures.
6. **`comp-purchase-order`** — needs the order-by date and suggested quantity from `comp-risk-engine` and the supplier from `comp-reference-data`. Nothing depends on it.
7. **`comp-scenario`** — re-runs `comp-demand-engine` and `comp-risk-engine` under an overlay, so both must exist first. `comp-chat-agent` depends on it.
8. **`comp-chat-agent`** — reads figures and traces from `comp-risk-engine` and scenario diffs from `comp-scenario`. Nothing depends on it; it is last precisely because it may only render what already exists.

> **This reorders the backlog.** The build-order snapshot in `docs/02-stories/backlog-draft.md` was computed **with tier 3 skipped**, because no module order existed. With this section in place, tier 3 now applies and the published `order-<nnn>` labels are stale. They should be recomputed (by `work-selector-agent` or by hand) once this document is approved. Flagged rather than left to diverge silently.

---

## 11. Architecture Decision Records

Append-only. Never edited, never renumbered, never deleted.

### ADR-001 — Modular monolith, not services
**Context.** Eight capability areas, a fixed deadline, two users, one kitchen.
**Decision.** One deployable service. Modules are enforced by folder boundaries and explicit interfaces; cross-module calls are function calls, not network calls.
**Alternatives.** A service per area — eight deployments, eight pipelines, and distributed-transaction problems for a dataset that fits in memory.
**Consequences.** Cheap, debuggable, and trivially satisfies REQ-031 because there is one process and one cache. If a module later needs independent scaling, the interface is already the seam.
**Drivers.** Constraints §fixed-deadline, REQ-031, REQ-032.
**Status.** Accepted.

### ADR-002 — Python + FastAPI backend, TypeScript + React frontend, with a generated client
**Context.** Python with FastAPI is the required backend platform. The browser client needs type safety across the API boundary, because REQ-031 requires that a figure shown on the dashboard and the same figure quoted by the Chat Agent be identical — and a silently drifted field name or shape is exactly how that requirement fails in production rather than in CI.
**Decision.** The service is **Python 3.12 + FastAPI**, with **Pydantic v2** response models and **SQLAlchemy 2.0** for persistence. The client is **TypeScript + React 18 + Vite**. The two are joined by the **OpenAPI 3.1 schema FastAPI emits**: CI regenerates the TypeScript client from it and **fails the build if the committed client differs from the regenerated one**. Hand-editing the generated client is prohibited.
**Alternatives.** Flask or Django — neither gives typed response models and a generated OpenAPI schema as a first-class property, and that schema is what makes the two-language split safe here. Hand-written frontend types — drift is invisible until a figure disagrees, which is the REQ-031 failure itself. Server-rendered Python templates — the dashboard and Chat Agent are interactive surfaces (REQ-018–020, REQ-033), and re-rendering a page per scenario preview does not meet REQ-033.
**Consequences.** Two toolchains (uv/pip + pytest, npm + vitest) and two CI jobs. The domain model is defined once in Pydantic and derived everywhere else, so the duplication is generated rather than maintained. Python's `Decimal` and `int` give exact arithmetic for REQ-028 without a third-party numeric library. Python 3.12.10 and Node 22.23.2 are both verified present per `PROJECT.md`.
**Drivers.** Stated platform requirement; REQ-028, REQ-029, REQ-031, REQ-033.
**Status.** Accepted.

### ADR-003 — AWS App Runner for the API
**Context.** REQ-032 requires the dashboard to be materially faster than the few-second chat budget.
**Decision.** App Runner, container from ECR, minimum one instance, running uvicorn.
**Alternatives.** Lambda behind API Gateway — cold starts work directly against REQ-032 (and a Python image with SQLAlchemy is not a fast cold start), and reaching RDS requires VPC attachment plus RDS Proxy, more moving parts than the whole rest of this design. ECS/Fargate — the same always-warm property for considerably more Terraform. EC2 — patching burden.
**Consequences.** A standing cost even when idle, which for this system is the price of REQ-032. `PROJECT.md` already names App Runner as the intended deploy target, so this is not a new commitment.
**Drivers.** REQ-032, REQ-033, Constraints §fixed-deadline.
**Status.** Accepted.

### ADR-004 — PostgreSQL on RDS
**Context.** REQ-004 aggregates ingredient demand across every dish containing that ingredient — a join over Dish × Recipe × Ingredient. REQ-029 requires traces be reconstructible.
**Decision.** RDS PostgreSQL 16, `db.t4g.micro`, single-AZ, private subnet.
**Alternatives.** DynamoDB — single-table modelling of a three-way join buys nothing at 40 ingredients and makes REQ-004 awkward. Aurora Serverless v2 — the ACU floor exceeds t4g.micro at this scale. Flat JSON in S3 — no home for credentials (REQ-043) or editable configuration (REQ-012).
**Consequences.** Single-AZ accepts a restore-from-snapshot RTO. Appropriate at this scale; revisit if an RPO is ever stated (assumption A-5).
**Drivers.** REQ-004, REQ-012, REQ-029, REQ-039, REQ-043.
**Status.** Accepted.

### ADR-005 — React SPA on S3 + CloudFront
**Context.** Desktop/tablet browser only; REQ-032; REQ-034.
**Decision.** React 18 + Vite, built to static assets, served from S3 behind CloudFront.
**Alternatives.** Server-side rendering — no SEO requirement and no first-paint requirement exists to pay for it.
**Consequences.** The client deploys independently of the API, which is what lets `comp-web-client` sit third in the build order against contracts alone.
**Drivers.** Constraints §platform, REQ-032, REQ-034.
**Status.** Accepted.

### ADR-006 — The LLM never computes a number
**Context.** REQ-030 forbids the explanation layer from independently estimating any quantity; REQ-031 requires its figures match the dashboard; REQ-028 requires determinism. The Success Metrics make steps 3 and 5 — both Chat Agent steps — the acceptance-critical ones, and state that a vague or inconsistent answer at either fails acceptance regardless of how the dashboard looks.
**Decision.** Arithmetic lives exclusively in `comp-demand-engine`, `comp-risk-engine` and `comp-scenario`. `comp-chat-agent` receives an explicit set of `{label, value, unit, source}` tuples and may only compose sentences from them. A validator parses every numeral out of the model's output and rejects the turn if any numeral is not in the supplied set. The module split between `comp-chat-agent` and `comp-scenario` exists to make this structurally enforceable rather than a convention.
**Alternatives.** Give the model tool access to the raw data and let it compute — fails REQ-028 outright and makes REQ-031 unenforceable.
**Consequences.** Any figure the manager can ask about must first exist as a computed figure. If a question needs a number nobody computed, the correct behaviour is to say so — not to estimate.
**Drivers.** REQ-028, REQ-029, REQ-030, REQ-031, Success Metrics steps 3 and 5.
**Status.** Accepted.

### ADR-007 — Amazon Bedrock as the model provider
**Context.** REQ-013 and REQ-017 require natural language; REQ-033 bounds the response time.
**Decision.** Bedrock (Claude family) via `boto3`, streamed to the browser as a FastAPI `StreamingResponse`; model id held in configuration.
**Alternatives.** A direct third-party API — a second vendor, a second credential path and egress out of the account, for no capability this design uses.
**Consequences.** One IAM policy governs model access. Switching models is a configuration change.
**Drivers.** REQ-013, REQ-017, REQ-033, REQ-036.
**Status.** Accepted.

### ADR-008 — All money is integer paise
**Context.** REQ-011 multiplies a quantity by a unit cost; REQ-027 sums those across every warning including suppressed ones; REQ-028 requires identical output on every run.
**Decision.** A single `Paise` type — a Python `int`, a Postgres `BIGINT`, a TypeScript `number` at the render edge only. No `float` touches a money value anywhere in the service. Formatting to `₹` happens only in `comp-web-client`.
**Alternatives.** `float` — summation order changes the last paisa, which is a REQ-028 failure and a REQ-031 inconsistency between dashboard and chat. `Decimal` for money — correct, but an `int` of paise makes the invariant unbreakable rather than merely observed.
**Consequences.** Quantities that are not whole (grams, litres) are held as `Decimal` with a declared scale, never `float`; the rounding step to paise is explicit, documented, and appears in the trace. Pydantic serialisers are configured to emit paise as integers, so JSON never carries a float money value across the language boundary.
**Drivers.** REQ-011, REQ-027, REQ-028, REQ-031, REQ-035.
**Status.** Accepted.

### ADR-009 — Every published figure carries its trace
**Context.** REQ-029 requires every figure be reconstructible as an explicit arithmetic trace back to the input data.
**Decision.** Engine functions return a Pydantic `Traced[T]` model — `{value, trace}`, where `trace` is an ordered list of steps terminating in input rows. No engine returns a bare number across a module boundary, and the type system enforces it.
**Alternatives.** A separate provenance service labelled onto a third of the backlog — makes traceability an add-on that can be forgotten per call site. Reconstructing traces on demand — a second code path that can disagree with the first, failing REQ-031.
**Consequences.** Slightly larger payloads; REQ-029 becomes a type-level guarantee rather than a testing aspiration, and REQ-030's validator gets its input for free.
**Drivers.** REQ-029, REQ-030, REQ-031.
**Status.** Accepted.

### ADR-010 — Per-user login built in-application; supersedes ARCH-016
**Context.** The prior Solution Architecture (Confluence page id 5885984847, **ARCH-016**) specifies *a single shared email+password login*. PRD v1.5 records that the client **rejected** that framing, and v1.6 confirms the correction: two personas, `kitchen-manager` and `fb-manager`, each with their own distinct credential set (REQ-044), with identical access once authenticated (OQ-9). The PRD explicitly names the architecture as the document that must change, not the PRD.
**Decision.** A `users` table with two rows and distinct credentials. Argon2id password hashing. An HttpOnly, `SameSite=Lax`, signed session cookie. No role column and no authorisation layer, because OQ-9 resolved to identical access. No MFA (OQ-6), no self-service password reset (OQ-7), no idle timeout (OQ-8) — reset is manager/support-assisted, executed as a seeded hash update.
**Alternatives.** Amazon Cognito — its value is MFA, hosted reset flows and token lifecycle, which are exactly the three things the client removed; a user-pool dependency for two rows is not warranted.
**Consequences.** **ARCH-016 is stale and is superseded by this ADR.** The companion Security Architecture document's open MFA marker is resolved as out of scope by OQ-6. Sessions never expiring is a deliberate, client-accepted posture, recorded as a risk in §12 rather than a defect.
**Drivers.** REQ-043, REQ-044, OQ-6, OQ-7, OQ-8, OQ-9.
**Status.** Accepted. **Supersedes ARCH-016.**

### ADR-011 — A what-if scenario is a pure overlay, never persisted
**Context.** REQ-017–020 require recomputation; the Non-Goals forbid saving, naming or comparing scenarios.
**Decision.** `comp-scenario` builds an in-memory `ScenarioOverlay` on top of the immutable baseline snapshot, re-runs the same engine functions, and returns a diff. Nothing is written to the database. The baseline listing is untouched, so leaving the scenario is free.
**Alternatives.** A scenario table with a lifecycle — builds persistence the Non-Goals exclude, and creates a state the dashboard could silently show as real.
**Consequences.** Two scenarios in a row are independent requests, which is exactly what the journeys describe. Making the scenario-adjusted view visually distinct is a design-stage concern, already flagged in `journeys.md`.
**Drivers.** REQ-017, REQ-018, REQ-019, REQ-020, Non-Goals §scenario persistence.
**Status.** Accepted.

### ADR-012 — GitHub Actions with OIDC, Terraform for infrastructure
**Context.** GitHub Actions and AWS are the stated delivery platform.
**Decision.** Actions assumes an AWS role via OIDC — no long-lived keys in repository secrets. Terraform describes every resource; `terraform plan` is posted to the pull request and `apply` against `prod` is a gated step.
**Alternatives.** IAM access keys in secrets (a standing credential with no rotation story). CDK (one-language consistency, but the reviewable plan is worth more at a human gate). Console changes (not reproducible).
**Consequences.** Infrastructure changes are reviewed as a diff, which is what `CONVENTIONS.md` §6 needs the human to be shown.
**Drivers.** `CONVENTIONS.md` §6, Constraints §fixed-deadline.
**Status.** Accepted.

### ADR-013 — Hosting region
**Context.** `PROJECT.md` records `aws_region: us-east-1`. The product is an Indian kitchen operation priced in INR (REQ-035), with latency requirements in REQ-032 and REQ-033. A round trip from India to `us-east-1` costs roughly 200–250 ms before any work is done.
**Decision.** Deploy to `us-east-1` as recorded, **pending confirmation**. `ap-south-1` (Mumbai) is the better fit on latency and on any data-residency expectation the PRD does not state.
**Alternatives.** `ap-south-1` — better latency and residency; requires confirming Bedrock model availability there.
**Consequences.** If `ap-south-1` is chosen, the change is a Terraform variable plus a model-availability check. Making it before first deploy is nearly free; making it after is a migration.
**Drivers.** REQ-032, REQ-033; `PROJECT.md`.
**Status.** **Proposed — blocked by the region/residency question in §12.** Settled by a stated hosting region or data-residency obligation in the PRD.

### ADR-015 — Deploy as one Lambda behind a Function URL, not App Runner
**Context.** The brief after v1.1 was to reach a working build by the fastest and simplest route, with AWS and GitHub Actions kept as hard requirements. App Runner (ADR-003) needs an ECR repository, a container build, an image push and a service — four resources and a registry — and it bills continuously whether anyone opens the dashboard or not.
**Decision.** One Lambda function (Python 3.12, arm64, 1024 MB) behind a **Lambda Function URL**, with `Mangum` adapting the ASGI app. No API Gateway, no VPC, no load balancer, no container registry. The same function also serves the browser client's static files, so there is no second deploy target.
**Alternatives.** App Runner (ADR-003) — better on REQ-032, worse on everything else at this stage. API Gateway in front of the Lambda — a second resource that buys nothing here, since a Function URL already provides HTTPS and the application does its own authentication.
**Consequences.** **This trades away ADR-003's always-warm property.** A cold start costs roughly 1–2 seconds on the first request after idle, which a strict reading of REQ-032 would fail. Warm requests are well inside the assumed target (A-2). Provisioned concurrency restores the guarantee for a few rupees a day if it matters; the decision is one parameter, not a rewrite. Flagged as a risk in §12 rather than glossed over.
**Drivers.** Explicit instruction to build the fastest, simplest thing; Constraints §fixed-deadline; AWS retained as a requirement.
**Status.** Accepted. **Supersedes ADR-003 for the v1 deployment.** ADR-003's reasoning stands and is the upgrade path if REQ-032 is tightened.

### ADR-016 — Supplied datasets ship with the build; only mutable state needs a store
**Context.** ADR-004 chose RDS PostgreSQL. Re-reading the PRD: all six Input Data categories are *supplied, fixed, and never sourced or inferred by the system*, and the Non-Goals exclude ongoing data entry. The only thing that actually changes at runtime is the materiality threshold (REQ-012). One mutable value does not justify a database server, a VPC, a subnet group, a security group and a connection pool.
**Decision.** The six datasets ship as JSON inside the deployment package and are loaded once per cold start. The mutable state — the materiality threshold and the forward horizon — lives in a **single DynamoDB table**, pay-per-request. Locally, that same store falls back to a JSON file, so development needs no AWS account.
**Alternatives.** RDS PostgreSQL (ADR-004) — the right answer once data is entered rather than supplied, and the wrong cost for a read-only dataset of a few hundred kilobytes. Storing the datasets in DynamoDB too — rows that never change, paid for on every read. S3 — one more resource for no gain over the package itself.
**Consequences.** **REQ-004's join is done in Python, not SQL** — over 37 ingredients and 84 recipe lines this is microseconds, and the arithmetic trace (REQ-029) is easier to build in code than in a query. Changing the supplied data is a redeploy; that is correct, because the PRD says the data is supplied rather than entered. If ongoing data entry ever enters scope, ADR-004 is the decision to return to.
**Drivers.** PRD §Input Data, PRD §Non-Goals (ongoing data entry), REQ-012, Constraints §fixed-deadline.
**Status.** Accepted. **Supersedes ADR-004 for the v1 deployment.**

### ADR-017 — The browser client is plain HTML, CSS and JavaScript
**Context.** ADR-005 chose React + Vite on S3 + CloudFront. That is a second toolchain, a second deploy target, a CDN invalidation step and, under ADR-002, a generated-client contract job to keep types aligned.
**Decision.** The client is three static files served by the Lambda. No framework, no bundler, no npm, no build step.
**Alternatives.** React + Vite (ADR-005) — worth it for a large interface with deep component reuse; this is four screens.
**Consequences.** ADR-002's generated TypeScript client is **not needed**, because there is no TypeScript — and with it goes the cross-language drift risk that §12 flagged as the cost of the required platform. The trade is that the UI has no type checking at all, so the API contract is enforced by the tests rather than by a compiler. Reintroducing React later touches only `src/web/`.
**Drivers.** Explicit instruction to build the simplest thing; Constraints §platform, §fixed-deadline.
**Status.** Accepted. **Supersedes ADR-005 and the client half of ADR-002 for the v1 deployment.**

### ADR-018 — AWS SAM instead of Terraform
**Context.** ADR-012 chose Terraform for reviewability. The infrastructure is now two resources.
**Decision.** One SAM template. `sam build && sam deploy` creates the function, the URL, the table, the IAM policy and the log group.
**Alternatives.** Terraform (ADR-012) — better at scale and for multi-provider estates; more to author and a state backend to host for two resources.
**Consequences.** The changeset SAM prints before applying serves the same review purpose the Terraform plan did, so `CONVENTIONS.md` §6's requirement that a human sees what will change still holds. The GitHub Actions and OIDC half of ADR-012 is unchanged.
**Drivers.** Explicit instruction to build the simplest thing; `CONVENTIONS.md` §6.
**Status.** Accepted. **Supersedes the Terraform half of ADR-012.**

### ADR-019 — The Chat Agent composes deterministically; Bedrock is optional
**Context.** ADR-006 forbids the language layer from computing. ADR-007 chose Bedrock to generate the prose. But a model call needs model access granted in the region, adds latency against REQ-033, and introduces the one component that can say something the engines did not compute.
**Decision.** Intent classification is keyword and date-grammar based; the answer is composed from the engines' finished figures by template. Setting `PHRASING_BACKEND=bedrock` adds a Bedrock pass that may **reword only** — it receives the finished text and the exact figure set, and a validator rejects any numeral it introduces that is not in that set, falling back to the deterministic text.
**Alternatives.** Bedrock composing every answer (ADR-007) — better phrasing, and the thing most likely to fail acceptance steps 3 and 5, which the client says fail the product outright if the answer is vague or inconsistent.
**Consequences.** Runs with no model access and no credentials. REQ-030 and REQ-031 hold by construction. **The cost is real: phrasing the parser does not recognise gets a plain "I could not understand that" rather than a graceful answer.** `journeys.md` already records unparseable input as a PRD gap with no defined behaviour; saying so plainly is the reading that cannot invent a figure. Widening the parser, or enabling the Bedrock pass, are both incremental.
**Drivers.** REQ-013, REQ-017, REQ-030, REQ-031, REQ-033, REQ-036, Success Metrics steps 3 and 5.
**Status.** Accepted. **Narrows ADR-007** — Bedrock remains the provider when phrasing is enabled.

### ADR-020 — PBKDF2-HMAC-SHA256 instead of Argon2id
**Context.** ADR-010 specified Argon2id. `argon2-cffi` is a compiled wheel, which means building the Lambda package for the target architecture rather than zipping pure Python.
**Decision.** PBKDF2-HMAC-SHA256 at 240,000 iterations, from the standard library.
**Alternatives.** Argon2id (ADR-010) — memory-hard and the better choice; costs a platform-specific build step.
**Consequences.** **This is the weakest link in the build and is deliberately recorded as such.** PBKDF2 is materially easier to attack with commodity hardware than Argon2id. It is defensible while the system holds two demo credentials and no customer data. **It should not stand when this holds a real credential** — recorded as a risk in §12, not as a settled position.
**Drivers.** REQ-043, REQ-044; packaging simplicity.
**Status.** Accepted **for the demo build only**. Revert to ADR-010 before any real use.

### ADR-014 — Configuration is data, not code
**Context.** REQ-012 requires the materiality threshold be adjustable without redeployment. REQ-007/REQ-039 require a per-ingredient or per-supplier safety margin.
**Decision.** The materiality threshold and forward horizon live in a `Configuration` table; the safety margin lives on Ingredient and Supplier. Defaults are seeded (₹500, 14 days), never compiled in. A missing safety margin is surfaced as a data gap, never defaulted to zero.
**Alternatives.** Environment variables — a threshold change becomes a deploy, failing REQ-012. Hardcoded constants — explicitly forbidden by REQ-012.
**Consequences.** Changing the threshold recomputes suppression and the aggregate live. Because REQ-027 counts suppressed warnings too, the aggregate is invariant under threshold changes — a useful property to assert in a test.
**Drivers.** REQ-007, REQ-012, REQ-027, REQ-039.
**Status.** Accepted.

---

## 12. Risks, assumptions and open items

**Assumptions** — A-1 to A-6 in §3. Each stands in for a requirement the PRD does not state. None is cited anywhere in this document as if the client had said it.

**Questions returned to agent 01 (the PRD agent) to mint as `OQ-` ids.** This agent does not mint `OQ-` ids; `CONVENTIONS.md` §2 assigns that to agent 01.

| Question | Blocks |
|---|---|
| Expected concurrency and request volume | Nothing today (A-1) |
| Quantified targets for REQ-032 and REQ-033 — both are relative, and "materially faster" is not testable as written | Acceptance testability of REQ-032/033 |
| Required accessibility standard, and the supported browser/device matrix | Nothing today (A-3, A-4); costly if answered late |
| Hosting region and any data-residency obligation | **ADR-013** |
| Data retention, backup retention, RPO/RTO | Database tier in ADR-004 (A-5) |
| Credential-handling obligations now that REQ-043/044 store emails and password hashes — the Non-Goals line "no personal, customer or payment data is involved" predates the login and is now inaccurate | Nothing today (A-6); a stale sentence in a Confirmed PRD |

**Risks**

| Risk | Consequence | Mitigation |
|---|---|---|
| Sessions never expire (OQ-8, client-accepted) | A session cookie on a shared kitchen tablet stays valid indefinitely | Documented as an accepted posture in ADR-010; explicit logout is provided. Worth re-raising if the tablet is genuinely shared. |
| REQ-032 and REQ-033 are relative, not absolute | QA cannot write a pass/fail test as worded | A-2 gives provisional numbers so tests can exist; they need PRD ratification |
| `us-east-1` latency from India | 200–250 ms added to every request, against REQ-032 | ADR-013, unresolved |
| ~~Two languages across the API boundary~~ | — | **Retired in v1.2.** ADR-017 removed TypeScript from the build, so there is no second language to drift against. Returns if React does. |
| **Lambda cold start (ADR-015)** | The first request after an idle period costs roughly 1–2 seconds, which a strict reading of **REQ-032** fails | Warm requests are well inside the A-2 target. Provisioned concurrency restores the guarantee for a few rupees a day, or return to ADR-003's App Runner. One parameter, not a rewrite. |
| **PBKDF2 instead of Argon2id (ADR-020)** | Password hashes are materially cheaper to attack than the architecture intended | Acceptable while the system holds two demo credentials and no customer data. **Must revert to ADR-010 before this holds a real credential.** |
| **No type checking in the browser client (ADR-017)** | An API field renamed in Python and not in `app.js` fails at runtime, not at build time | The API journey tests exercise every field the client reads. Reintroducing React and the generated client is confined to `src/web/`. |
| **Short-shelf-life ingredients are permanently at stockout risk** | A 14-day horizon against a 2-day shelf life means the projection always exhausts stock inside the window, so fresh herbs, milk and prawns sit on the dashboard every day | Not a defect — it is REQ-005 read literally, and it was visible as soon as real figures ran. It does mean the dashboard's usefulness depends on the manager reading the order-by date rather than the flag. Worth putting to the client: either the horizon becomes per-ingredient, or these items are expected to be a standing reorder list. |
| `comp-web-client` carries 13 of 30 stories | A broad module; a UI defect's `comp-` label discriminates less than the others | The `screen-*` axis from agent 04 is the intended discriminator for visual defects (`CONVENTIONS.md` §3). Not a boundary error, but the reason the design stage matters here. |
| `comp-auth` and `comp-purchase-order` own one story each | A module owning a single story is usually not a module | Both kept deliberately: `comp-auth` is a distinct trust boundary gating every route, small only because the client removed MFA, reset and timeout; `comp-purchase-order` produces a distinct output artifact from a distinct area. Flagged honestly rather than merged to look tidier. |
| Backlog read from a cache, not from Jira | Story assignments in §13 drift if Jira changed since the 2026-09-17 sync | Re-verify against Jira before the `comp-*` write-back |
| Published `order-<nnn>` labels are now stale | Work selection ranks on an ordering computed without tier 3 | §10 — recompute after approval |

---

## 13. Story → module assignment

30 stories, **0 unassigned**.

| `comp-*` | Stories | Count |
|---|---|---|
| `comp-reference-data` | US-025, US-026, US-027, US-028 | 4 |
| `comp-auth` | US-030 | 1 |
| `comp-demand-engine` | US-001, US-002 | 2 |
| `comp-risk-engine` | US-003, US-004, US-005, US-006, US-007, US-008, US-009, US-019, US-023, US-029 | 10 |
| `comp-scenario` | US-014, US-015, US-016, US-017 | 4 |
| `comp-chat-agent` | US-010, US-011, US-012, US-013, US-014 | 5 |
| `comp-purchase-order` | US-018 | 1 |
| `comp-web-client` | US-009, US-018, US-019, US-020, US-021, US-022, US-023, US-024, US-025, US-026, US-027, US-028, US-030 | 13 |

**Stories carrying two `comp-` labels (11 of 30).** US-009 (threshold logic is engine, the adjust control is a screen), US-014 (parsing is chat, recompute is scenario), US-018, US-019 (cross-type ranking is engine, rendering is screen), US-023 (aggregate is engine, display is screen), US-024–US-028, US-030. Under half the backlog, and each genuinely spans a compute module and its screen — the split the design stage's `screen-*` axis complements.

---

## 14. Requirement coverage

All 44 requirements (REQ-001 – REQ-044) are implemented by at least one module. **No coverage gaps.**

| Requirements | Module |
|---|---|
| REQ-001 – REQ-004 | `comp-demand-engine` |
| REQ-005 – REQ-009 | `comp-risk-engine` |
| REQ-010 – REQ-012, REQ-042 | `comp-risk-engine` |
| REQ-013 – REQ-016, REQ-036 | `comp-chat-agent` |
| REQ-017 – REQ-020 | `comp-scenario` (compute), `comp-chat-agent` (surface) |
| REQ-021, REQ-022 | `comp-purchase-order` |
| REQ-023 – REQ-027 | `comp-risk-engine` (ranking, aggregate), `comp-web-client` (render) |
| REQ-028 – REQ-031 | Cross-cutting — ADR-006, ADR-008, ADR-009; enforced in the engines |
| REQ-032, REQ-033 | ADR-003 (always warm), ADR-007 (streaming) |
| REQ-034 | `comp-web-client` |
| REQ-035 | ADR-008, all modules |
| REQ-037 – REQ-041 | `comp-reference-data`, `comp-web-client` |
| REQ-043, REQ-044 | `comp-auth` |

---

## 15. Outstanding pipeline actions

1. **Approval of this document**, which is also approval of the module build order in §10 (`CONVENTIONS.md` §5 tier 3).
2. **`comp-*` write-back to Jira — NOT performed.** Jira was excluded from this run by instruction. Once approved, each story in §13 needs `comp-<module>` plus `stage-03-architected` appended to its **existing** labels (never replacing them), and its `Components: TBD (set by architecture agent)` line updated. Re-read each issue's live labels first.
3. **Recompute the build-order snapshot** now that tier 3 has an input (§10).
4. **ARCH-016 (Confluence page 5885984847) is superseded by ADR-010** and should be annotated as such, along with the companion Security Architecture document's MFA marker (resolved out of scope by OQ-6).
5. **Six questions returned to agent 01** (§12) for minting as `OQ-` ids.
6. **`PROJECT.md` needs updating** — `cloud_provider` reads `none`; this design commits to `aws`. The `aws` CLI and `gh` CLI degradations recorded there remain unresolved and will block agents 05, 06 and 09.

---

## Change Log

| Version | Date | Added | Changed | Retired |
|---|---|---|---|---|
| 1.0 | 2026-09-18 | Initial design against PRD v1.6. Modules `comp-reference-data`, `comp-auth`, `comp-demand-engine`, `comp-risk-engine`, `comp-scenario`, `comp-chat-agent`, `comp-purchase-order`, `comp-web-client`. ADR-001 – ADR-014. | ARCH-016 (prior Solution Architecture) superseded by ADR-010 | — |
| 1.2 | 2026-09-18 | **ADR-015 – ADR-020**, recording the simplifications taken to reach a working build fastest, with AWS and GitHub Actions kept as requirements. Lambda + Function URL; datasets in the package + DynamoDB for mutable state; plain HTML/JS client; SAM; deterministic Chat Agent with optional Bedrock; PBKDF2. New risks in §12: cold start against REQ-032, PBKDF2, no client type checking, and short-shelf-life ingredients being permanently at stockout risk. | ADR-003, ADR-004, ADR-005, the Terraform half of ADR-012 and the client half of ADR-002 are **superseded for the v1 deployment**, each naming its successor; ADR-007 is **narrowed** by ADR-019. Superseded ADRs are left intact and unedited, per the append-only rule — each remains the upgrade path if its requirement is tightened. Module boundaries, build order, story assignment and requirement coverage are **unchanged**. | Cross-language drift risk (no longer applicable) |
| 1.1 | 2026-09-18 | Generated-client contract job in CI; cross-language drift and two-toolchain risks in §12 | **Backend language set to Python 3.12 + FastAPI by stated platform requirement.** ADR-002 rewritten from "TypeScript end to end" to "Python + FastAPI backend, TypeScript + React frontend, joined by a generated OpenAPI client"; §1, §5, §8, §9 and ADR-003, ADR-007, ADR-008, ADR-009 updated to match. ADR-002 was **revised in place rather than superseded**, because v1.0 was never approved — no accepted decision was edited. Module boundaries, build order, story assignment and requirement coverage are **unchanged**. | — |
