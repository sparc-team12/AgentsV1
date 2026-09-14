# Architecture: Premium Perfume E-Commerce

**Version:** 1.1 | **Status:** Draft | **Last Updated:** 2026-09-13
**PRD designed against:** `1. PRD/prd-premium-perfume-ecommerce.md` @ v1.2
**Project:** ACRI | **cloudId:** 69a5faff-afbd-40dc-ac75-1b2a52db5362

## Change Log
| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-13 | Initial draft against PRD v1.1. Stack partially blocked: hosting, auth, caching marked Proposed — blocked by OQ-4 (empty Non-Functional bucket). |
| 1.1 | 2026-09-13 | PRD amended to v1.2 (OQ-4, OQ-1 resolved; REQ-016–REQ-023 added). ADR-001 (hosting), ADR-002 (auth), ADR-003 (caching) unblocked and finalized as Accepted, scoped to small-scale/PCI SAQ-A profile. REQ-009 shipping-provider-interface seam formalized as ADR-007 (Accepted). Added ADR-008 (PCI SAQ-A / payment offload, REQ-018/019), ADR-009 (accessibility/browser support, REQ-020/021), ADR-010 (7-year data retention, REQ-022 — note: PRD's own REQ-023 is retention, not the shipping interface; coordinator's message numbered these differently, this document follows the PRD verbatim). Stack table updated: no application caching layer or managed-auth-provider needed at <100 concurrent users. |

## Step 1 — NFR gate

**Resolved in v1.2.** PRD Non-Functional bucket now carries REQ-016–REQ-023:

- REQ-016 — ≥100 concurrent shoppers at launch (small scale)
- REQ-017 — p95 page-load < 2.5s
- REQ-018 — PCI SAQ-A: no card data stored, delegated to hosted payment gateway
- REQ-019 — platform stores customer PII (name, address, order history)
- REQ-020 — WCAG 2.1 AA
- REQ-021 — evergreen browsers (Chrome/Firefox/Safari/Edge, last 2 versions)
- REQ-022 — mobile-responsive layout
- REQ-023 — 7-year retention for customer/order records

All previously-blocked ADRs (hosting, auth, caching) are now unblocked and finalized below. REQ-009 was reworded (still v1 must-have) to require an abstract shipping-provider interface with vendor selection deferred — OQ-1 resolved, so this is now a firm design requirement, not an open question.

## Step 2 — area → comp map

| area | comp | rationale |
|---|---|---|
| catalog | `comp-catalog` | single data owner (SKU/fragrance), read-heavy, changes at content-update rate |
| cart | `comp-cart` | session/user-scoped state, different lifecycle (ephemeral) from catalog |
| checkout | `comp-checkout` | owns Order creation, distinct from cart (cart is pre-purchase, checkout is transactional) |
| accounts | `comp-accounts` | owns Shopper identity/auth; wishlist (REQ-015, later) stays here — shares Shopper data model |
| admin | `comp-admin` | owns operator-facing inventory + order views; reads/writes Order and SKU stock, but as a distinct UI/permission surface |
| *(new)* | `comp-platform` | shared cross-cutting concerns: auth session validation, notification (order confirmation), no owning REQ alone — supports REQ-007, REQ-009, REQ-011 |

No area implied `comp-notification` as a story-bearing module since no story owns it yet (order confirmation is implicit in REQ-007/009); folded into `comp-platform` rather than invented as a phantom module with zero stories.

`comp-catalog` absorbs REQ-014 (reviews, later) — same entity ownership (SKU), no split warranted; will revisit if reviews grow into their own moderation workflow.

## Step 3 — Design

### Stack (finalized)

| Layer | Choice | Drivers | Rejected |
|---|---|---|---|
| Language/runtime | Node.js (TypeScript) | REQ constraint: custom-built, not page-builder; budget Rs 5-10L favors one language front+back, fast hiring in India | Java/Spring (heavier for 20-story v1 scope, slower to budget) |
| Web framework | Next.js (React) | REQ-001..006 catalog/search/filter UX, SSR for SEO (new brand needs discoverability — inferred, Assumption), REQ-022 mobile-responsive layout | Plain SPA (weaker SEO for a new-brand storefront) |
| API style | REST (framework routes) | Small module count (6), no polyglot clients yet | GraphQL (unjustified complexity for this scope) |
| Datastore | PostgreSQL, single managed instance | Relational data (SKU/Order/Shopper), ACID for stock decrement (REQ-010) and order integrity (REQ-011); REQ-016's ≥100 concurrent load is well within a single small managed instance | MongoDB (rejected, no schema-flex need beats transactions); clustered/sharded Postgres (rejected, over-built for REQ-016's stated scale) |
| Hosting | Single-region managed PaaS (one app instance + managed Postgres + managed static/CDN for assets), autoscale off at launch | REQ-016 (≥100 concurrent — one small instance covers this with headroom), budget/timeline constraints (managed PaaS minimizes ops effort for a 6-month build) | Self-managed VM/containers (more ops overhead, no benefit at this scale); multi-region (unjustified — single-country nationwide delivery, no stated multi-region traffic) |
| Auth | Self-rolled session-based auth: server-side sessions in Postgres, bcrypt password hashing, HTTPS/TLS everywhere | REQ-008 (signup/login), REQ-019 (PII stored — needs access control), REQ-018 (SAQ-A — card data never touches platform, so platform auth doesn't need to meet card-handling PCI controls) | Third-party managed auth provider (Auth0/Clerk) — rejected, recurring cost not justified against budget when self-rolled session auth meets the stated security scope (no card data, small user base) |
| Caching | None at launch — no application/data cache layer; rely on browser cache + CDN for static assets only | REQ-017 (p95 < 2.5s) is achievable without a cache at 30 SKUs and ≤100 concurrent users; REQ-016 confirms small scale | Redis/in-memory cache (rejected — added operational cost with no load to justify it; revisit if REQ-016's concurrency target rises) |
| Payment | Hosted payment gateway (vendor TBD, REQ-013 later) behind a `PaymentProvider` interface; card data never touches the platform | REQ-018 (PCI SAQ-A scope) | Storing/processing card data directly (rejected — would raise PCI scope far beyond SAQ-A) |

Budget check: managed PaaS + managed Postgres + no third-party auth/cache recurring costs keeps monthly spend low, fitting Rs 5-10L total for a 6-month build.

### Modules

**comp-catalog** — owns product discovery and content. Data: `Fragrance`, `SKU`. Area: catalog. Stories: US-001..US-008.

**comp-cart** — owns pre-purchase basket state. Data: `Cart`, `CartLine`. Area: cart. Stories: US-009, US-010.

**comp-checkout** — owns order placement and delivery-fee logic. Data: `Order`, `OrderLine`, `DeliveryPolicy`. Area: checkout. Stories: US-011, US-012, US-013.

**comp-accounts** — owns shopper identity and (later) wishlist. Data: `Shopper`, `Wishlist`, `WishlistItem`. Area: accounts. Stories: US-014..US-017.

**comp-admin** — owns operator-facing stock/order surfaces (reads/writes `SKU.stockLevel` and `Order.status`, owned schema-wise by comp-catalog/comp-checkout respectively, but the operator UI/permission logic is its own module). Area: admin. Stories: US-018..US-021.

**comp-platform** — shared: session/auth validation, order-status notification hook. No stories assigned yet (cross-cutting; will pick up REQ-009 courier integration once OQ-1 resolves).

### Data model (entity names from PRD Glossary)

- **Fragrance** (id, name, category [men's/women's/unisex], description) — owned by comp-catalog
- **SKU** (id, fragranceId, size, price, stockLevel) — owned by comp-catalog; stockLevel mutated by comp-admin (REQ-010)
- **Shopper** (id, email, passwordHash, createdAt) — owned by comp-accounts
- **Cart** (id, shopperId, status) / **CartLine** (cartId, skuId, quantity) — owned by comp-cart
- **Order** (id, shopperId, status, deliveryFee, placedAt) / **OrderLine** (orderId, skuId, quantity, priceAtOrder) — owned by comp-checkout; status mutated by comp-admin (REQ-011)
- **DeliveryPolicy** — not a persisted entity in v1 (single nationwide free-delivery rule, REQ-012); modeled as a constant/config, not a table, until multiple rules exist
- **Wishlist** (id, shopperId) / **WishlistItem** (wishlistId, skuId) — later (REQ-015), owned by comp-accounts
- **Review** (id, skuId, shopperId, rating, text) — later (REQ-014), owned by comp-catalog

Relationships: Fragrance 1—N SKU; Shopper 1—N Cart (one active); Cart 1—N CartLine; Shopper 1—N Order; Order 1—N OrderLine; OrderLine N—1 SKU.

### API surface (operation-level)

- `comp-catalog`: `GET /skus`, `GET /skus/{id}`, `GET /skus?search=`, `GET /skus?category=&size=&priceMin=&priceMax=` (REQ-001..005)
- `comp-cart`: `GET /cart`, `POST /cart/lines`, `PATCH /cart/lines/{id}`, `DELETE /cart/lines/{id}` (REQ-006)
- `comp-checkout`: `POST /orders` (creates from cart, applies free-delivery, COD only) (REQ-007, REQ-012); `GET /orders/{id}` (REQ-009, blocked by OQ-1 for real tracking status)
- `comp-accounts`: `POST /shoppers` (signup), `POST /sessions` (login) (REQ-008)
- `comp-admin`: `GET /admin/skus`, `PATCH /admin/skus/{id}/stock` (REQ-010); `GET /admin/orders`, `PATCH /admin/orders/{id}/status` (REQ-011)
- Internal seam: `comp-checkout` → `comp-catalog` (stock check/decrement on order placement) — in-process call or same-DB transaction, not yet a network seam given single-deployment scale assumption (Assumption, see Risks).

### Integration points

- **Courier/logistics partner** (REQ-009) — OQ-1 resolved: vendor selection deferred by client decision, not merely unanswered. Design finalized behind a `ShippingProvider` interface (trackOrder, nationwide-coverage check); comp-platform hosts a stub/manual implementation (admin-set status) until a real vendor is plugged in. See ADR-007.
- **Payment gateway** (REQ-013, later; REQ-018 PCI scope) — vendor still TBD, but the seam is now a firm requirement (not just a good idea): `PaymentProvider` interface, hosted/redirect-based flow so card data never reaches comp-checkout. See ADR-008.
- No email/SMS provider named for order-confirmation notifications — still an inferred need (not a stated REQ); remains an Assumption in Risks.

### NFR strategy

| REQ | Strategy |
|---|---|
| REQ-016 (≥100 concurrent) | Single managed app instance + managed Postgres sized for this load (see ADR-001); no scale-out needed at launch |
| REQ-017 (p95 < 2.5s) | SSR via Next.js, no cache layer needed at 30-SKU catalog size, CDN for static assets (see ADR-003) |
| REQ-018 (PCI SAQ-A) | Card data never enters the platform; hosted payment gateway via `PaymentProvider` interface (ADR-008) |
| REQ-019 (PII storage) | `Shopper`/`Order` entities store name/address/order history in Postgres with access control via session auth; no card data co-located (ADR-002, ADR-008) |
| REQ-020 (WCAG 2.1 AA) | Enforced at UI-component level in comp-catalog/comp-cart/comp-checkout/comp-accounts frontend build; not a backend/module concern (ADR-009) |
| REQ-021 (evergreen browsers) | Next.js default browser target; no legacy-browser polyfill budget (ADR-009) |
| REQ-022 (mobile-responsive) | Responsive layout is a frontend requirement across all shopper-facing modules (catalog, cart, checkout, accounts) (ADR-009) |
| REQ-023 (7-year retention) | `Shopper` and `Order` records (and line items) are never hard-deleted within 7 years; soft-delete/archival policy in comp-accounts and comp-checkout schemas (ADR-010) |

### ADRs

**ADR-001 — Hosting/deployment topology**
Context: Need to host Next.js + Postgres app. Decision: single-region managed PaaS, one app instance + managed Postgres, autoscale off at launch. Alternatives: self-managed VM (rejected — more ops overhead for no benefit at this scale), containers on cloud (rejected — over-engineered for REQ-016's stated load), multi-region (rejected — no cross-border/multi-region traffic implied). Drivers: REQ-016 (≥100 concurrent — small scale), budget/timeline constraints. Status: **Accepted** (v1.1, unblocked by OQ-4 resolution).

**ADR-002 — Auth mechanism**
Context: REQ-008 requires shopper signup/login; comp-admin needs operator auth too; REQ-019 confirms PII is stored; REQ-018 confirms card data never touches the platform. Decision: self-rolled session-based auth (server-side sessions in Postgres, bcrypt password hashing, HTTPS/TLS everywhere). Alternatives: third-party managed auth provider (rejected — recurring cost not justified once PCI scope is confirmed narrow (SAQ-A) and user base is small); JWT stateless auth (rejected — session revocation is simpler to reason about for this scale and no stated need for stateless/multi-service auth). Drivers: REQ-008, REQ-018, REQ-019. Status: **Accepted** (v1.1, unblocked by OQ-4 resolution).

**ADR-003 — Caching strategy**
Context: catalog is read-heavy (REQ-001..006), only 30 SKUs; REQ-017 sets p95 < 2.5s; REQ-016 confirms ≤100 concurrent users. Decision: no application/data cache layer at launch; CDN + browser caching for static assets only. Alternatives: Redis/in-memory cache (rejected — no load justifies the added operational cost; revisit if REQ-016's concurrency target rises materially post-launch). Drivers: REQ-016, REQ-017. Status: **Accepted** (v1.1, unblocked by OQ-4 resolution).

**ADR-004 — Datastore under load**
Context: PostgreSQL chosen for relational integrity (see stack table). Decision: PostgreSQL — this part is **Accepted** regardless of NFRs, since it derives from REQ-010/011 transactional needs, not from load. Sizing/replication strategy is what's blocked. Alternatives considered: MongoDB (rejected — no need for schema flexibility beats transaction needs). Drivers: REQ-010, REQ-011. Status: **Accepted** (core choice); replication/scaling sub-decision **Proposed — blocked by OQ-4**.

**ADR-005 — Module boundary: comp-admin as separate from comp-catalog/comp-checkout**
Context: Admin operations (REQ-010, REQ-011) mutate data owned by catalog and checkout modules. Decision: keep comp-admin as its own module for permission/UI boundary, not a separate data owner. Alternatives: fold admin views into comp-catalog/comp-checkout directly (rejected — mixes operator and shopper-facing permission models). Drivers: REQ-010, REQ-011. Status: **Accepted**.

**ADR-006 — DeliveryPolicy not modeled as a table**
Context: REQ-012, single nationwide free-delivery rule, no tiers. Decision: model as application constant, not a DB entity. Alternatives: a `DeliveryPolicy` table (rejected — no second rule exists to justify it; would be speculative). Drivers: REQ-012. Status: **Accepted**.

**ADR-007 — Order tracking behind an abstract shipping-provider interface**
Context: REQ-009 (reworded in PRD v1.2) requires order tracking built behind a `ShippingProvider` interface, with courier/logistics vendor selection deferred (OQ-1 resolved as "defer, don't pick now"). Decision: comp-checkout exposes `GET /orders/{id}` against a `ShippingProvider` interface (methods: `trackOrder`, `nationwideCoverageCheck`); comp-platform ships a stub implementation (admin-set status: placed/processing/shipped/delivered) until a real courier is integrated. Alternatives: hardcode a specific courier now (rejected — no vendor chosen, and PRD explicitly defers this); no tracking at all until a vendor exists (rejected — REQ-009 is a v1 must-have, interface satisfies it without a vendor). Drivers: REQ-009. Status: **Accepted**.

**ADR-008 — PCI SAQ-A via hosted payment gateway interface**
Context: REQ-018 requires the platform to never store card/payment data, keeping it in PCI SAQ-A scope; REQ-013 (later) will add online payment. Decision: define a `PaymentProvider` interface now (redirect/hosted-fields based) so comp-checkout never receives raw card data even when REQ-013 is built later; vendor selection remains open (no vendor named in PRD). Alternatives: store/process card data directly (rejected — would raise PCI scope far beyond SAQ-A, contradicts REQ-018 explicitly). Drivers: REQ-018, REQ-013. Status: **Accepted** (interface-level decision; vendor selection remains a separate, later decision — not blocking).

**ADR-009 — Accessibility and browser support as a frontend cross-cutting concern**
Context: REQ-020 (WCAG 2.1 AA), REQ-021 (evergreen browser support), REQ-022 (mobile-responsive). Decision: these are enforced at the frontend/component level across all shopper-facing modules (comp-catalog, comp-cart, comp-checkout, comp-accounts), not as a separate module — no distinct data ownership or deployment shape is implied. Alternatives: a dedicated `comp-accessibility` module (rejected — this is a cross-cutting UI concern, not a data/capability owner; would violate the "module = capability, not a layer" rule). Drivers: REQ-020, REQ-021, REQ-022. Status: **Accepted**.

**ADR-010 — 7-year data retention via soft-delete/archival, not hard delete**
Context: REQ-023 requires customer and order records retained for 7 years. Decision: `Shopper` and `Order` (plus `OrderLine`) records use soft-delete/archival flags rather than hard deletion; no automated purge job runs before the 7-year mark. Alternatives: hard delete on account closure (rejected — directly violates REQ-023). Drivers: REQ-023. Status: **Accepted**.

### Risks & assumptions

- **Assumption**: single-region deployment, single-instance DB sufficient for v1 launch (no traffic figures given). Cost if wrong: re-architecture for scale-out post-launch.
- **Assumption**: SEO/discoverability matters enough to justify SSR (Next.js) — not a stated REQ, inferred from "new venture, no existing brand" in Problem Statement. Cost if wrong: unnecessary framework complexity vs a plain SPA.
- **Assumption**: order-confirmation notification (email/SMS) is needed even though no REQ states it — commonly implicit in checkout flows. Cost if wrong: scope creep if built before confirmed; flagged, not built into MVP API surface as a hard requirement.
- **Risk**: REQ-009 (order tracking) has no real courier integration until OQ-1 resolves — `comp-checkout`'s `GET /orders/{id}` will return internal status only (placed/processing/shipped-manually-updated by admin) until a provider is chosen.
- **Risk**: comp-admin mutating comp-catalog/comp-checkout-owned tables directly means those two modules must agree on schema ownership; documented in ADR-005, but implementation must not let comp-admin bypass validation logic that lives in the owning module.

## Coverage check

All 12 v1 must-have REQs (001-012) and all 3 later REQs (013-015) map to a module. REQ-009 still has no Jira story (story-index gap predates OQ-1's resolution — a story now needs to be raised by the user-stories agent against the reworded REQ-009); the design seam is finalized (ADR-007). All 8 Non-Functional REQs (016-023) now have a documented strategy; none require a new module — they are satisfied by stack choices (016, 017), the payment-interface seam (018), data-model/retention decisions (019, 023), and frontend cross-cutting practice (020, 021, 022).

**Note on requirement numbering**: the coordinator's task message described a "REQ-023 (via reworded REQ-009)" for the shipping interface and REQ-022 for retention; the PRD v1.2 itself numbers these REQ-009 (shipping interface, unchanged id, reworded text) and REQ-023 (7-year retention). This document follows the PRD verbatim as the source of truth.
