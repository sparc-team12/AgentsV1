# Component Index — Premium Perfume E-Commerce

**This is a cache for fast local lookup — Jira is the source of truth.** Regenerate on every architecture sync; verify against Jira before relying on this for a decision.

**Architecture version:** 1.1 | **PRD designed against:** `1. PRD/prd-premium-perfume-ecommerce.md` @ v1.2
**Jira site:** experionglobal.atlassian.net
**cloudId:** 69a5faff-afbd-40dc-ac75-1b2a52db5362
**Project:** ACRI
**Synced:** 2026-09-13

## area → comp map

| area | comp |
|---|---|
| catalog | comp-catalog |
| cart | comp-cart |
| checkout | comp-checkout |
| accounts | comp-accounts |
| admin | comp-admin |
| *(none — cross-cutting)* | comp-platform (no stories yet; auth/notification/shipping-stub support) |

## Modules

| comp-module | Responsibility | US-ids | REQ-ids |
|---|---|---|---|
| comp-catalog | Product discovery: browse, search, filter, detail page, reviews (later) | US-001, US-002, US-003, US-004, US-005, US-006, US-007, US-008 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-014 |
| comp-cart | Pre-purchase basket state | US-009, US-010 | REQ-006 |
| comp-checkout | Order placement, free-delivery logic, payment (later) | US-011, US-012, US-013 | REQ-007, REQ-012, REQ-013, REQ-009 (tracking endpoint), REQ-018 |
| comp-accounts | Shopper identity, wishlist (later) | US-014, US-015, US-016, US-017 | REQ-008, REQ-015, REQ-019 |
| comp-admin | Operator inventory and order management UI/permission surface | US-018, US-019, US-020, US-021 | REQ-010, REQ-011 |
| comp-platform | Cross-cutting: session/auth validation, shipping-provider stub, notification hook | none yet | REQ-016, REQ-017, REQ-020, REQ-021, REQ-022, REQ-023 (supporting, not story-owning) |

## Notes

- REQ-009 (order tracking behind shipping-provider interface) has no Jira story yet — flagged for the user-stories agent; the design seam lives in comp-checkout/comp-platform (see architecture.md ADR-007).
- Non-Functional REQs (016-023) are satisfied by stack/design decisions, not by a dedicated module — see architecture.md NFR strategy table.
- comp-platform carries no `comp-` label writes in this run since no story exists to own it; it will pick one up once a shipping/notification story is raised.
