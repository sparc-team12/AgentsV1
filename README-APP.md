# Ingredient Demand Forecasting Assistant

Implements PRD v1.6 (`docs/01-prd/prd-ingredient-demand-forecasting.md`) against the
architecture in `docs/03-architecture/architecture.md`.

A kitchen manager opens one screen and can answer: what am I about to run out of and
by when must I order it; what am I about to throw away and what is it worth; why is
this flagged; and what happens if I change the menu.

---

## Run it locally

```bash
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload --app-dir src
```

Open <http://127.0.0.1:8000>.

To enable Chat Agent prose rewording (optional — see "the language layer never
computes a number" below), copy `.env.example` to `.env` at the repo root and
fill in `GEMINI_API_KEY` (or the Bedrock equivalents). `.env` is loaded
automatically and is git-ignored; never commit it.

| Persona | Email | Password |
|---|---|---|
| `kitchen-manager` | kitchen.manager@example.com | kitchen-demo-2026 |
| `fb-manager` | fb.manager@example.com | fandb-demo-2026 |

Both see exactly the same thing — OQ-9 resolved to identical access.

Interactive API docs are at `/docs`.

## Run the tests

```bash
python -m pytest tests/ -q
```

`tests/test_api_journeys.py` walks the PRD's own six-step acceptance sequence
through the HTTP API. `tests/test_acceptance.py` covers the requirement-level
behaviour — severity bands, the order-by arithmetic, determinism, and the rule
that the aggregate exposure counts warnings the materiality threshold hides.

## Deploy to AWS

Infrastructure is one SAM template: **one Lambda behind a Function URL** and
**one DynamoDB table**. No API Gateway, no VPC, no RDS, no container registry,
no S3 bucket for the frontend — the Lambda serves the browser client itself.

```bash
sam build
sam deploy --guided        # first time only; answers are saved to samconfig.toml
```

Thereafter GitHub Actions does it: `.github/workflows/deploy.yml` runs the tests
on every push and pull request, and deploys `main` to `dev`. Use the workflow's
manual trigger to deploy `prod`.

### What the pipeline needs

Repository **secrets**:

| Secret | Purpose |
|---|---|
| `AWS_ROLE_ARN` | An IAM role for GitHub OIDC. **Preferred.** |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Fallback if you have not set up OIDC yet. |
| `SESSION_SECRET` | HMAC key for the session cookie. Any long random string. |
| `KITCHEN_MANAGER_PASSWORD`, `FB_MANAGER_PASSWORD` | The two personas' passwords. |

Repository **variable**: `AWS_REGION` (defaults to `us-east-1`).

Target account is `092338124082` per `PROJECT.md`.

---

## How it is put together

Eight modules, matching the `comp-*` slugs in `docs/03-architecture/component-index.md`.
Seven are Python packages inside one FastAPI service (ADR-001, modular monolith);
one is the browser client.

| Module | File | Owns |
|---|---|---|
| `comp-reference-data` | `src/app/reference_data.py`, `domain.py`, `config.py` | The six supplied datasets, the canonical domain types, configuration |
| `comp-auth` | `src/app/auth.py` | Per-user login and the session cookie |
| `comp-demand-engine` | `src/app/demand_engine.py` | Demand projection and recipe-mapped ingredient demand |
| `comp-risk-engine` | `src/app/risk_engine.py` | Stockout and spoilage assessment, severity, ranking, aggregate exposure |
| `comp-scenario` | `src/app/scenario.py` | What-if overlay, recompute and diff |
| `comp-chat-agent` | `src/app/chat_agent.py` | Intent parsing and prose composition |
| `comp-purchase-order` | `src/app/purchase_order.py` | The editable order draft |
| `comp-web-client` | `src/web/` | Every screen |

### Three decisions worth knowing before you read the code

**The language layer never computes a number** (ADR-006). Every rupee figure and
every date comes from `demand_engine`, `risk_engine` or `scenario`, and each one
carries a `trace` listing the arithmetic behind it. The Chat Agent is handed
those finished figures and may only put them in sentences. That is what makes
REQ-030 and REQ-031 hold structurally rather than by review. Set
`PHRASING_BACKEND=bedrock` (Amazon Bedrock) or `PHRASING_BACKEND=gemini`
(Google AI Studio, needs `GEMINI_API_KEY` — see `.env.example`) to have an LLM
reword the prose — either gets the same finished figures, and any numeral it
introduces that the engines did not produce is rejected and the deterministic
text is used instead.

**Determinism is structural** (REQ-028). `today` is always a parameter, never
read from a clock inside an engine; every aggregation iterates a `sorted()`
sequence; money is an integer count of paise and quantities are `Decimal`, so no
float rounding can make two identical runs disagree.

**A missing safety margin is a gap, not a zero.** If neither the ingredient nor
its supplier carries one, no order-by date is computed and the ingredient is
reported as a data gap. Silently assuming zero would produce an order-by date
that looks authoritative and is wrong, which is the one failure the product
exists to prevent.

### Data

`src/data/*.json` holds the six supplied input categories: 18 dishes, 37
ingredients, 4 suppliers, 84 recipe lines, 12 weeks of daily sales. The PRD
states input data is supplied and never inferred, so it ships with the build.
`python scripts/seed_data.py` regenerates it deterministically; CI checks the
regenerated copy matches the committed one.

### Configuration

| Variable | Default | Notes |
|---|---|---|
| `APP_TODAY` | `2026-09-18` | REQ-028 — the explicit "today" the dataset is dated around |
| `TABLE_NAME` | unset | DynamoDB table. Unset means a local JSON file, so local dev needs no AWS. |
| `SESSION_SECRET` | dev placeholder | Must be set in any deployed environment |
| `PHRASING_BACKEND` | unset | `bedrock` to enable the optional rewording pass |

The materiality threshold is **not** an environment variable — REQ-012 requires
it be adjustable without a redeploy, so it lives in the state store and the
kitchen manager changes it from the dashboard.

---

## Known deviations from `architecture.md` v1.1

Taken to reach a working deployment fastest; each is a simplification, none
changes a module boundary or a requirement. See `architecture.md` v1.2 for the
recorded decisions.

| Architecture said | Built as | Why |
|---|---|---|
| App Runner + ECR container | Lambda + Function URL | No registry, no always-on cost, one resource instead of four |
| RDS PostgreSQL | JSON in the deployment package + DynamoDB for mutable state | The six input datasets are supplied and read-only; only the threshold changes. A database server for one mutable row is not worth a VPC. |
| React + Vite on S3/CloudFront | Plain HTML/CSS/JS served by the Lambda | No npm, no build step, no second deploy target, no CDN invalidation |
| Terraform | AWS SAM | One file, and `sam deploy` creates everything |
| Argon2id password hashing | PBKDF2-HMAC-SHA256 (standard library) | Keeps the Lambda package free of compiled wheels. **Weaker; revisit before this holds a real credential.** |
| Bedrock composes every answer | Deterministic composition, Bedrock optional | Needs no model access to run, cannot hallucinate, and satisfies REQ-033 trivially |

**Not yet done:** the `comp-*` and `stage-03-architected` labels have not been
written back to the Jira stories, and the `order-<nnn>` labels are stale now
that a module build order exists.
