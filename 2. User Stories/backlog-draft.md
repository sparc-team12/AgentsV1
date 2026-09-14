# Backlog Draft — Premium Perfume E-Commerce

**Source PRD:** `1. PRD/prd-premium-perfume-ecommerce.md` @ v1.1 (Status: Confirmed)
**Target Jira project:** ACRI ("Autonomous change request integration") — Epic, Story issue types confirmed available.
**Status:** DRAFT — not yet written to Jira. Awaiting explicit approval.

---

## Epics (feature areas)

| Epic | Area slug | REQ refs |
|---|---|---|
| [Catalog] Browse, search, and discover fragrances | `area-catalog` | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-014 |
| [Cart] Manage shopping cart | `area-cart` | REQ-006 |
| [Checkout] Place and pay for orders | `area-checkout` | REQ-007, REQ-012, REQ-013 |
| [Accounts] Shopper account and personalization | `area-accounts` | REQ-008, REQ-015 |
| [Admin] Store operations — inventory and order management | `area-admin` | REQ-010, REQ-011 |

No `area-platform` epic is created — the Non-Functional bucket is currently empty (see "Non-Functional requirements" section below), so there is nothing yet that warrants a standalone platform story.

No `area-orders` epic is created — its only candidate requirement, REQ-009 (shopper order tracking), is blocked by OQ-1 (see "Blocked" section). If OQ-1 is resolved, an `area-orders` epic should be introduced at that time.

---

## Summary Table

| Area | Story id | Summary | REQ refs | Phase |
|---|---|---|---|---|
| Catalog | US-001 | Shopper browses the fragrance catalog | REQ-001 | v1 |
| Catalog | US-002 | Shopper views a SKU's product detail page | REQ-001 | v1 |
| Catalog | US-003 | Shopper searches the catalog | REQ-002 | v1 |
| Catalog | US-004 | Shopper filters catalog by fragrance category | REQ-003 | v1 |
| Catalog | US-005 | Shopper filters catalog by size | REQ-004 | v1 |
| Catalog | US-006 | Shopper filters catalog by price | REQ-005 | v1 |
| Catalog | US-007 | Shopper views ratings and reviews on a product detail page | REQ-014 | later |
| Catalog | US-008 | Shopper submits a rating and review | REQ-014 | later |
| Cart | US-009 | Shopper adds a SKU to the cart | REQ-006 | v1 |
| Cart | US-010 | Shopper updates quantity or removes a SKU from the cart | REQ-006 | v1 |
| Checkout | US-011 | Shopper places a Cash-on-Delivery order | REQ-007 | v1 |
| Checkout | US-012 | Free delivery is applied automatically at checkout | REQ-012 | v1 |
| Checkout | US-013 | Shopper pays for an order via online payment gateway | REQ-013 | later |
| Accounts | US-014 | Shopper creates an account | REQ-008 | v1 |
| Accounts | US-015 | Shopper logs into their account | REQ-008 | v1 |
| Accounts | US-016 | Shopper adds a SKU to their wishlist | REQ-015 | later |
| Accounts | US-017 | Shopper views and manages their wishlist | REQ-015 | later |
| Admin | US-018 | Admin views stock levels across SKUs | REQ-010 | v1 |
| Admin | US-019 | Admin updates stock levels for a SKU | REQ-010 | v1 |
| Admin | US-020 | Admin views the list of orders and order details | REQ-011 | v1 |
| Admin | US-021 | Admin updates the status of an order | REQ-011 | v1 |

**Blocked** (no story drafted, per OQ-1):

| REQ | Requirement | Blocked by |
|---|---|---|
| REQ-009 | Order tracking: shopper can see the status of their order | OQ-1 — courier/logistics partner not yet selected. Order-status semantics (e.g. what "shipped"/"in transit" means, whether a tracking id/link is shown) cannot be made testable until a partner is named. |

---

## Non-Functional requirements

The PRD's Non-Functional bucket is empty — OQ-4 records that performance, security, accessibility, browser/device support and data retention were never discussed. There are consequently **no NFR ids to reference**. No story below carries an NFR-derived acceptance criterion, and no `area-platform` story (rate limiting, audit logging, consent banner, etc.) is created, because none is named in the PRD.

**Action needed before this backlog is fully sound:** once OQ-4 is answered and NFR ids (e.g. `REQ-016...`) are added to the PRD, this backlog must be revisited to (a) attach the relevant `req-` label + acceptance criterion to every constrained story, and (b) split out standalone platform stories for anything that needs its own implementation (rate limiting, audit trail, consent banner, etc.).

---

## Full Story Detail

### Epic: [Catalog] Browse, search, and discover fragrances (`area-catalog`)

#### US-001 — [Catalog] Shopper browses the fragrance catalog
**Labels:** `us-001`, `req-001`, `area-catalog`, `phase-v1`

**Story**
As a shopper, I want to browse the fragrance catalog, so that I can see what SKUs are available to buy.

**Acceptance Criteria**
1. Given the catalog contains SKUs, when a shopper opens the catalog page, then all 30 SKUs are listed with fragrance name, fragrance category, size, price and stock availability.
2. Given a SKU is out of stock, when the shopper views the catalog listing, then that SKU is visibly marked as out of stock.
3. Given the catalog page, when it loads with no filters or search applied, then SKUs are shown in a consistent default order (e.g. alphabetical by fragrance name).

**Traceability**
- Story-Id: US-001
- PRD-Ref: REQ-001
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: catalog
- Depends-On: none
- Components: TBD (set by architecture agent)

**Out of Scope**
- Product detail page content (US-002).
- Search and filtering (US-003–US-006).

---

#### US-002 — [Catalog] Shopper views a SKU's product detail page
**Labels:** `us-002`, `req-001`, `area-catalog`, `phase-v1`

**Story**
As a shopper, I want to view the detail page for a specific SKU, so that I can decide whether to buy it.

**Acceptance Criteria**
1. Given a valid SKU, when a shopper opens its detail page, then the fragrance name, fragrance category, size, price, and stock availability are displayed.
2. Given a SKU is out of stock, when the shopper views its detail page, then the page indicates it is out of stock and does not allow adding it to the cart.
3. Given an invalid or removed SKU id, when a shopper requests its detail page, then a "not found" state is shown instead of an error page.

**Traceability**
- Story-Id: US-002
- PRD-Ref: REQ-001
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: catalog
- Depends-On: US-001
- Components: TBD (set by architecture agent)

**Out of Scope**
- Ratings/reviews display (US-007) — v1 has no reviews per PRD Non-Goals.
- Adding the SKU to the cart (US-009).

---

#### US-003 — [Catalog] Shopper searches the catalog
**Labels:** `us-003`, `req-002`, `area-catalog`, `phase-v1`

**Story**
As a shopper, I want to search the catalog by keyword, so that I can quickly find a fragrance I'm looking for.

**Acceptance Criteria**
1. Given the catalog, when a shopper searches for a fragrance name that exists, then matching SKUs are returned.
2. Given a search term that matches no fragrance, when the shopper submits the search, then an empty-results state is shown (not an error).
3. Given a search term with only whitespace or special characters, when submitted, then the catalog handles it gracefully without a server error.

**Traceability**
- Story-Id: US-003
- PRD-Ref: REQ-002
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: catalog
- Depends-On: US-001
- Components: TBD (set by architecture agent)

**Out of Scope**
- Filtering by category/size/price (US-004–US-006).
- Search ranking/relevance tuning.

---

#### US-004 — [Catalog] Shopper filters catalog by fragrance category
**Labels:** `us-004`, `req-003`, `area-catalog`, `phase-v1`

**Story**
As a shopper, I want to filter the catalog by fragrance category (men's / women's / unisex), so that I only see fragrances relevant to me.

**Acceptance Criteria**
1. Given the catalog, when a shopper selects a fragrance category, then only SKUs in that category are shown.
2. Given a fragrance category with no in-stock SKUs, when selected, then an empty-results state is shown.
3. Given a category filter is active, when the shopper clears it, then the full catalog is shown again.

**Traceability**
- Story-Id: US-004
- PRD-Ref: REQ-003
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: catalog
- Depends-On: US-001
- Components: TBD (set by architecture agent)

**Out of Scope**
- Filtering by size or price (US-005, US-006).

---

#### US-005 — [Catalog] Shopper filters catalog by size
**Labels:** `us-005`, `req-004`, `area-catalog`, `phase-v1`

**Story**
As a shopper, I want to filter the catalog by size, so that I only see SKUs in the size I want.

**Acceptance Criteria**
1. Given the catalog, when a shopper selects a size, then only SKUs of that size are shown.
2. Given a size filter combined with a fragrance-category filter, when both are applied, then results satisfy both constraints simultaneously.
3. Given a size with no in-stock SKUs, when selected, then an empty-results state is shown.

**Traceability**
- Story-Id: US-005
- PRD-Ref: REQ-004
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: catalog
- Depends-On: US-001
- Components: TBD (set by architecture agent)

**Out of Scope**
- Filtering by category or price (US-004, US-006).

---

#### US-006 — [Catalog] Shopper filters catalog by price
**Labels:** `us-006`, `req-005`, `area-catalog`, `phase-v1`

**Story**
As a shopper, I want to filter the catalog by price, so that I only see SKUs within my budget.

**Acceptance Criteria**
1. Given the catalog, when a shopper sets a price range, then only SKUs priced within that range are shown.
2. Given a price range with no matching SKUs, when applied, then an empty-results state is shown.
3. Given an invalid price range (e.g. minimum greater than maximum), when submitted, then the catalog rejects it or corrects it without a server error.

**Traceability**
- Story-Id: US-006
- PRD-Ref: REQ-005
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: catalog
- Depends-On: US-001
- Components: TBD (set by architecture agent)

**Out of Scope**
- Filtering by category or size (US-004, US-005).

---

#### US-007 — [Catalog] Shopper views ratings and reviews on a product detail page
**Labels:** `us-007`, `req-014`, `area-catalog`, `phase-later`

**Story**
As a shopper, I want to see ratings and reviews on a SKU's detail page, so that I can judge quality before buying.

**Acceptance Criteria**
1. Given a SKU has reviews, when a shopper opens its detail page, then an average rating and individual reviews are displayed.
2. Given a SKU has no reviews yet, when a shopper opens its detail page, then a "no reviews yet" state is shown instead of an error.

**Traceability**
- Story-Id: US-007
- PRD-Ref: REQ-014
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: catalog
- Depends-On: US-002
- Components: TBD (set by architecture agent)

**Out of Scope**
- Submitting a review (US-008).
- Not part of v1 per PRD Non-Goals ("No customer reviews/ratings in v1"); build only when prioritized off the "Could Have" bucket.

---

#### US-008 — [Catalog] Shopper submits a rating and review
**Labels:** `us-008`, `req-014`, `area-catalog`, `phase-later`

**Story**
As a shopper, I want to submit a rating and review for a fragrance, so that I can share my experience with other shoppers.

**Acceptance Criteria**
1. Given a shopper is logged in, when they submit a rating and review for a SKU, then it is saved and becomes visible on that SKU's detail page.
2. Given a review submission with no rating selected, when submitted, then it is rejected with a clear validation message.
3. Given a shopper who is not logged in, when they attempt to submit a review, then they are prompted to log in first.

**Traceability**
- Story-Id: US-008
- PRD-Ref: REQ-014
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: catalog
- Depends-On: US-014, US-015
- Components: TBD (set by architecture agent)

**Out of Scope**
- Moderation/flagging of reviews.
- Not part of v1 per PRD Non-Goals.

---

### Epic: [Cart] Manage shopping cart (`area-cart`)

#### US-009 — [Cart] Shopper adds a SKU to the cart
**Labels:** `us-009`, `req-006`, `area-cart`, `phase-v1`

**Story**
As a shopper, I want to add a SKU to my cart, so that I can purchase it later at checkout.

**Acceptance Criteria**
1. Given an in-stock SKU, when a shopper adds it to the cart, then the cart reflects the added SKU and quantity.
2. Given a SKU is out of stock, when a shopper attempts to add it to the cart, then the action is blocked with a clear message.
3. Given a shopper adds more units of a SKU than are currently in stock, when they attempt to do so, then the quantity is capped at available stock with a clear message.

**Traceability**
- Story-Id: US-009
- PRD-Ref: REQ-006
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: cart
- Depends-On: US-001, US-002
- Components: TBD (set by architecture agent)

**Out of Scope**
- Updating quantity or removing items (US-010).
- Checkout (US-011).

---

#### US-010 — [Cart] Shopper updates quantity or removes a SKU from the cart
**Labels:** `us-010`, `req-006`, `area-cart`, `phase-v1`

**Story**
As a shopper, I want to update the quantity of a SKU in my cart or remove it, so that my cart reflects what I actually want to buy.

**Acceptance Criteria**
1. Given a SKU already in the cart, when the shopper increases or decreases its quantity within available stock, then the cart total updates accordingly.
2. Given a SKU already in the cart, when the shopper removes it, then it no longer appears in the cart and the total updates.
3. Given a shopper tries to set a quantity above current stock, when they do so, then the quantity is capped at available stock with a clear message.
4. Given a shopper empties the cart entirely, when they view it, then an empty-cart state is shown.

**Traceability**
- Story-Id: US-010
- PRD-Ref: REQ-006
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: cart
- Depends-On: US-009
- Components: TBD (set by architecture agent)

**Out of Scope**
- Adding new SKUs to the cart (US-009).

---

### Epic: [Checkout] Place and pay for orders (`area-checkout`)

#### US-011 — [Checkout] Shopper places a Cash-on-Delivery order
**Labels:** `us-011`, `req-007`, `area-checkout`, `phase-v1`

**Story**
As a shopper, I want to check out my cart using Cash-on-Delivery, so that I can complete my purchase without paying online.

**Acceptance Criteria**
1. Given a non-empty cart, when a shopper completes checkout with a valid delivery address, then an order is created with payment method COD and the shopper sees an order confirmation.
2. Given a shopper reaches checkout with an empty cart, when they attempt to check out, then they are blocked with a clear message and no order is created.
3. Given a SKU in the cart goes out of stock between add-to-cart and checkout, when the shopper attempts to check out, then they are notified and the order is not placed with the unavailable SKU.
4. Given a shopper submits checkout without required delivery address fields, when submitted, then validation errors are shown and no order is created.
5. Given an order is successfully placed, when checkout completes, then stock levels for the purchased SKUs are decremented.

**Traceability**
- Story-Id: US-011
- PRD-Ref: REQ-007
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: checkout
- Depends-On: US-009, US-010
- Components: TBD (set by architecture agent)

**Out of Scope**
- Online payment gateway (US-013) — Non-Goal in v1, COD only.
- GST-compliant invoicing — explicit PRD Non-Goal.
- Free-delivery fee logic (US-012).

---

#### US-012 — [Checkout] Free delivery is applied automatically at checkout
**Labels:** `us-012`, `req-012`, `area-checkout`, `phase-v1`

**Story**
As a shopper, I want free delivery applied automatically at checkout regardless of my location in India, so that I am never charged a delivery fee.

**Acceptance Criteria**
1. Given a shopper checks out with a delivery address anywhere in India, when the order total is calculated, then no delivery fee is added to the order total.
2. Given the order confirmation and order summary, when displayed, then delivery cost is explicitly shown as free (e.g. "₹0" or "Free"), not simply omitted.

**Traceability**
- Story-Id: US-012
- PRD-Ref: REQ-012
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: checkout
- Depends-On: US-011
- Components: TBD (set by architecture agent)

**Out of Scope**
- Courier/logistics partner selection and shipment tracking — see OQ-1, tied to REQ-009 (blocked).
- International delivery (out of PRD scope entirely — India only).

---

#### US-013 — [Checkout] Shopper pays for an order via online payment gateway
**Labels:** `us-013`, `req-013`, `area-checkout`, `phase-later`

**Story**
As a shopper, I want to pay for my order online via a payment gateway, so that I don't have to pay cash on delivery.

**Acceptance Criteria**
1. Given a non-empty cart, when a shopper chooses online payment at checkout, then they are directed to a payment step and the order is only confirmed after successful payment.
2. Given a payment attempt fails or is declined, when this happens, then the shopper is notified and no order is created (or the order is marked payment-failed), and stock is not decremented.
3. Given a payment gateway timeout or network failure occurs, when this happens, then the shopper sees a clear error and can retry without being double-charged.

**Traceability**
- Story-Id: US-013
- PRD-Ref: REQ-013
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: checkout
- Depends-On: US-011
- Components: TBD (set by architecture agent)

**Out of Scope**
- Not part of v1 per PRD ("No online payment gateway integration in v1 — COD only"); build only when prioritized off the "Could Have" bucket.

---

### Epic: [Accounts] Shopper account and personalization (`area-accounts`)

#### US-014 — [Accounts] Shopper creates an account
**Labels:** `us-014`, `req-008`, `area-accounts`, `phase-v1`

**Story**
As a shopper, I want to create an account, so that I can check out faster and track my orders.

**Acceptance Criteria**
1. Given valid account details (e.g. name, email/phone, password), when a shopper submits account creation, then the account is created and the shopper is signed in.
2. Given an email/phone already registered, when a shopper attempts to create an account with it, then the attempt is rejected with a clear message.
3. Given missing or invalid required fields, when account creation is submitted, then validation errors are shown and no account is created.

**Traceability**
- Story-Id: US-014
- PRD-Ref: REQ-008
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: accounts
- Depends-On: none
- Components: TBD (set by architecture agent)

**Out of Scope**
- Login for an existing account (US-015).
- Password reset / account recovery flows (not mentioned in PRD — flag if needed later).

---

#### US-015 — [Accounts] Shopper logs into their account
**Labels:** `us-015`, `req-008`, `area-accounts`, `phase-v1`

**Story**
As a shopper, I want to log into my account, so that I can access my order history and saved details.

**Acceptance Criteria**
1. Given valid credentials, when a shopper logs in, then they are authenticated and taken to their account context.
2. Given invalid credentials, when a shopper attempts to log in, then access is denied with a clear, non-specific error message.
3. Given repeated failed login attempts, when they occur, then the shopper is not told which field (email vs password) was wrong (basic enumeration protection) — exact throttling behaviour pending OQ-4 (account security not yet discussed).

**Traceability**
- Story-Id: US-015
- PRD-Ref: REQ-008
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: accounts
- Depends-On: US-014
- Components: TBD (set by architecture agent)

**Out of Scope**
- Account creation (US-014).
- Multi-factor authentication or advanced security controls — not specified in PRD; revisit once OQ-4 is answered.

---

#### US-016 — [Accounts] Shopper adds a SKU to their wishlist
**Labels:** `us-016`, `req-015`, `area-accounts`, `phase-later`

**Story**
As a shopper, I want to add a SKU to my wishlist, so that I can find it easily later without buying it now.

**Acceptance Criteria**
1. Given a shopper is logged in and viewing a SKU, when they add it to their wishlist, then it appears in their wishlist.
2. Given a shopper is not logged in, when they attempt to add a SKU to a wishlist, then they are prompted to log in first.
3. Given a SKU is already in the wishlist, when the shopper adds it again, then no duplicate entry is created.

**Traceability**
- Story-Id: US-016
- PRD-Ref: REQ-015
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: accounts
- Depends-On: US-002, US-014, US-015
- Components: TBD (set by architecture agent)

**Out of Scope**
- Viewing/managing the wishlist (US-017).
- Not part of v1 per PRD Non-Goals ("No wishlist feature in v1"); build only when prioritized off the "Could Have" bucket.

---

#### US-017 — [Accounts] Shopper views and manages their wishlist
**Labels:** `us-017`, `req-015`, `area-accounts`, `phase-later`

**Story**
As a shopper, I want to view and manage my wishlist, so that I can revisit or remove saved SKUs.

**Acceptance Criteria**
1. Given a shopper has SKUs in their wishlist, when they open their wishlist, then all saved SKUs are listed with current price and stock availability.
2. Given a shopper removes a SKU from the wishlist, when they do so, then it no longer appears there.
3. Given a wishlisted SKU goes out of stock, when the shopper views their wishlist, then it is clearly marked out of stock rather than hidden.

**Traceability**
- Story-Id: US-017
- PRD-Ref: REQ-015
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: accounts
- Depends-On: US-016
- Components: TBD (set by architecture agent)

**Out of Scope**
- Adding items to the wishlist (US-016).
- Not part of v1 per PRD Non-Goals.

---

### Epic: [Admin] Store operations — inventory and order management (`area-admin`)

#### US-018 — [Admin] Admin views stock levels across SKUs
**Labels:** `us-018`, `req-010`, `area-admin`, `phase-v1`

**Story**
As an admin, I want to view current stock levels across all SKUs, so that I know what needs replenishing.

**Acceptance Criteria**
1. Given the store has 30 SKUs, when an admin opens the inventory view, then current stock count for each SKU is shown.
2. Given a SKU's stock has dropped to zero, when the admin views inventory, then it is clearly flagged as out of stock.

**Traceability**
- Story-Id: US-018
- PRD-Ref: REQ-010
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: admin
- Depends-On: none
- Components: TBD (set by architecture agent)

**Out of Scope**
- Editing stock levels (US-019).

---

#### US-019 — [Admin] Admin updates stock levels for a SKU
**Labels:** `us-019`, `req-010`, `area-admin`, `phase-v1`

**Story**
As an admin, I want to update the stock level for a SKU, so that the catalog reflects what is actually available (~1000 units total across 30 SKUs).

**Acceptance Criteria**
1. Given a SKU, when an admin sets a new stock quantity, then the catalog and cart availability reflect the update immediately.
2. Given an admin attempts to set a negative stock quantity, when submitted, then it is rejected with a validation message.
3. Given stock is updated to zero, when this happens, then the SKU becomes unavailable for adding to cart across the storefront.

**Traceability**
- Story-Id: US-019
- PRD-Ref: REQ-010
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: admin
- Depends-On: US-018
- Components: TBD (set by architecture agent)

**Out of Scope**
- Viewing stock levels (US-018).
- Automated reordering/supplier integration (not in PRD).

---

#### US-020 — [Admin] Admin views the list of orders and order details
**Labels:** `us-020`, `req-011`, `area-admin`, `phase-v1`

**Story**
As an admin, I want to view the list of orders and each order's details, so that I can fulfil them.

**Acceptance Criteria**
1. Given orders exist, when an admin opens the orders view, then a list of orders is shown with shopper, SKUs, quantities, total, and current status.
2. Given a specific order, when an admin opens its detail view, then the delivery address, COD payment method, and free-delivery indicator are shown.
3. Given no orders exist yet, when the admin opens the orders view, then an empty state is shown.

**Traceability**
- Story-Id: US-020
- PRD-Ref: REQ-011
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: admin
- Depends-On: US-011
- Components: TBD (set by architecture agent)

**Out of Scope**
- Updating order status (US-021).
- Shopper-facing order tracking (REQ-009) — blocked by OQ-1, not covered by this story.

---

#### US-021 — [Admin] Admin updates the status of an order
**Labels:** `us-021`, `req-011`, `area-admin`, `phase-v1`

**Story**
As an admin, I want to update the status of an order (e.g. processing, dispatched, delivered, cancelled), so that I can manage fulfilment.

**Acceptance Criteria**
1. Given an order in "processing" status, when an admin marks it "dispatched", then the order's status updates accordingly.
2. Given an order an admin wants to cancel, when they mark it "cancelled", then stock for its SKUs is restored.
3. Given an invalid status transition (e.g. moving a "delivered" order back to "processing"), when attempted, then it is rejected with a clear message.

**Traceability**
- Story-Id: US-021
- PRD-Ref: REQ-011
- PRD-Doc: 1. PRD/prd-premium-perfume-ecommerce.md @ v1.1
- Area: admin
- Depends-On: US-020
- Components: TBD (set by architecture agent)

**Out of Scope**
- Exposing this status directly to the shopper as real-time tracking — that is REQ-009, blocked by OQ-1.
- Courier/carrier integration.

---

## Gaps and flags for approval

**Coverage gap:** none among the Must/Should/Could Have buckets — every REQ-001..015 except REQ-009 has at least one story. REQ-009 is intentionally unstoried, see Blocked above.

**Blocked by open question:**
- REQ-009 (order tracking) — blocked by OQ-1 (courier/logistics partner not yet selected). No stories drafted; will need US-022+ once OQ-1 is resolved.

**NFR ids not referenced by any story:** none exist — the PRD's Non-Functional bucket is empty (OQ-4). This itself is the gap: no story in this backlog currently carries any performance, security, accessibility, browser/device, or data-retention acceptance criterion. Recommend the client answer OQ-4 before/alongside build start, since NFRs constrain nearly every story above (catalog load performance, account security limits en route to US-015, accessibility for the whole storefront, etc.).

**Scope creep check:** no story was added beyond what traces to an explicit REQ id. US-007/008 (reviews) and US-016/017 (wishlist) exist only because REQ-014/REQ-015 exist in the "Could Have" bucket — labelled `phase-later` accordingly, not `phase-v1`.

**Other observations:**
- OQ-2 (success metrics) and OQ-3 (competitor/UX direction) do not block any requirement per the PRD and are not referenced by any story.
- No Jira `components` were set on any story — no components list was found in project ACRI's metadata to validate names against; architecture agent to set `comp-<module>` labels later per schema.
