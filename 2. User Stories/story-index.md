# Story Index — Premium Perfume E-Commerce

**This is a cache for fast local lookup — Jira is the source of truth.** Regenerate on every sync; verify against Jira before relying on this for a decision.

**Jira site:** experionglobal.atlassian.net
**cloudId:** 69a5faff-afbd-40dc-ac75-1b2a52db5362
**Project:** ACRI
**PRD synced:** `1. PRD/prd-premium-perfume-ecommerce.md` @ **v1.1**
**Synced:** 2026-09-13

## Epics

| Area | Jira key | REQ refs |
|---|---|---|
| catalog | ACRI-3 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-014 |
| cart | ACRI-4 | REQ-006 |
| checkout | ACRI-5 | REQ-007, REQ-012, REQ-013 |
| accounts | ACRI-6 | REQ-008, REQ-015 |
| admin | ACRI-7 | REQ-010, REQ-011 |

## Stories

| US-id | Jira key | Area | REQ refs | Summary | Phase |
|---|---|---|---|---|---|
| US-001 | ACRI-8 | catalog | REQ-001 | Shopper browses the fragrance catalog | v1 |
| US-002 | ACRI-9 | catalog | REQ-001 | Shopper views a SKU's product detail page | v1 |
| US-003 | ACRI-10 | catalog | REQ-002 | Shopper searches the catalog | v1 |
| US-004 | ACRI-11 | catalog | REQ-003 | Shopper filters catalog by fragrance category | v1 |
| US-005 | ACRI-12 | catalog | REQ-004 | Shopper filters catalog by size | v1 |
| US-006 | ACRI-13 | catalog | REQ-005 | Shopper filters catalog by price | v1 |
| US-007 | ACRI-14 | catalog | REQ-014 | Shopper views ratings and reviews on a product detail page | later |
| US-008 | ACRI-15 | catalog | REQ-014 | Shopper submits a rating and review | later |
| US-009 | ACRI-16 | cart | REQ-006 | Shopper adds a SKU to the cart | v1 |
| US-010 | ACRI-17 | cart | REQ-006 | Shopper updates quantity or removes a SKU from the cart | v1 |
| US-011 | ACRI-18 | checkout | REQ-007 | Shopper places a Cash-on-Delivery order | v1 |
| US-012 | ACRI-19 | checkout | REQ-012 | Free delivery is applied automatically at checkout | v1 |
| US-013 | ACRI-20 | checkout | REQ-013 | Shopper pays for an order via online payment gateway | later |
| US-014 | ACRI-21 | accounts | REQ-008 | Shopper creates an account | v1 |
| US-015 | ACRI-22 | accounts | REQ-008 | Shopper logs into their account | v1 |
| US-016 | ACRI-23 | accounts | REQ-015 | Shopper adds a SKU to their wishlist | later |
| US-017 | ACRI-24 | accounts | REQ-015 | Shopper views and manages their wishlist | later |
| US-018 | ACRI-25 | admin | REQ-010 | Admin views stock levels across SKUs | v1 |
| US-019 | ACRI-26 | admin | REQ-010 | Admin updates stock levels for a SKU | v1 |
| US-020 | ACRI-27 | admin | REQ-011 | Admin views the list of orders and order details | v1 |
| US-021 | ACRI-28 | admin | REQ-011 | Admin updates the status of an order | v1 |

## Known gaps (carried from backlog-draft.md)

- **REQ-009** (order tracking) has no story — blocked by OQ-1 (courier/logistics partner not yet selected).
- **Non-Functional bucket is empty** (OQ-4 unresolved) — no story yet carries a performance/security/accessibility/data-retention acceptance criterion.
- **Depends-On links** are recorded in each story's description text but not yet created as real Jira issue links (`createIssueLink`) — fast-follow, not blocking.
- No `components` set on any story — none existed in ACRI to validate names against; architecture agent to add `comp-<module>` labels later.
