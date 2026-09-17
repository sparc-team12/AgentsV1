# Component Index — Ingredient Demand Forecasting Assistant

**This is a cache for fast local lookup, not the source of truth. Jira is authoritative.** If this file disagrees with Jira, Jira is right. Regenerate whenever the architecture is revised.

- **Architecture version:** 1.1 (Status: **Draft — awaiting approval**)
- **Stack:** Python 3.12 + FastAPI on AWS App Runner, RDS PostgreSQL, React/TypeScript SPA on S3 + CloudFront, Amazon Bedrock, GitHub Actions + Terraform
- **PRD version designed against:** v1.6 (Confirmed)
- **Backlog source:** `docs/02-stories/story-index.md` @ 2026-09-17 sync — 30 stories
- **Project:** `ACRI`
- **cloudId:** `69a5faff-afbd-40dc-ac75-1b2a52db5362`
- **Generated:** 2026-09-18

> **Not yet written to Jira.** No `comp-*` or `stage-03-architected` label has been applied. Jira was excluded from this run by instruction; the write-back is pending approval and a subsequent run with Jira access.

## area-* → comp-* map

| `area-*` | Primary `comp-*` | Also touches |
|---|---|---|
| `area-auth` | `comp-auth` | `comp-web-client` |
| `area-data-setup` | `comp-reference-data` | `comp-web-client` |
| `area-demand-projection` | `comp-demand-engine` | — |
| `area-stockout-risk` | `comp-risk-engine` | — |
| `area-spoilage-risk` | `comp-risk-engine` | — |
| `area-chat-agent` | `comp-chat-agent` | `comp-scenario` |
| `area-purchase-orders` | `comp-purchase-order` | `comp-web-client` |
| `area-dashboard` | `comp-web-client` | `comp-risk-engine` |

## Modules

Seven modules are Python packages inside the one FastAPI service; `comp-web-client` is the TypeScript browser application.

| `comp-` module | Responsibility | US-ids | REQ-ids | Build order |
|---|---|---|---|---|
| `comp-reference-data` | Loads, validates and serves the six supplied input datasets; owns the canonical domain types and configuration | US-025, US-026, US-027, US-028 | REQ-037–041, REQ-012, REQ-007 (margin storage) | 1 |
| `comp-auth` | Per-user authentication and session for the two personas; gates every route | US-030 | REQ-043, REQ-044 | 2 |
| `comp-web-client` | The browser application — every screen both personas see | US-009, US-018, US-019, US-020, US-021, US-022, US-023, US-024, US-025, US-026, US-027, US-028, US-030 | REQ-023–027, REQ-034, REQ-035, REQ-037–041, REQ-043 | 3 |
| `comp-demand-engine` | Dish demand projection and recipe-mapped ingredient demand | US-001, US-002 | REQ-001–004, REQ-028, REQ-029 | 4 |
| `comp-risk-engine` | Stockout and spoilage assessment, shared severity scale, order-by date, order quantity, waste cost, materiality suppression, aggregate exposure, combined ranking | US-003, US-004, US-005, US-006, US-007, US-008, US-009, US-019, US-023, US-029 | REQ-005–012, REQ-023, REQ-027, REQ-042, REQ-028, REQ-029 | 5 |
| `comp-purchase-order` | Editable purchase-order draft text for a stockout-risk ingredient | US-018 | REQ-021, REQ-022 | 6 |
| `comp-scenario` | What-if overlay and deterministic recompute + diff | US-014, US-015, US-016, US-017 | REQ-017–020, REQ-028 | 7 |
| `comp-chat-agent` | Natural-language intent parsing and prose composition over pre-computed figures | US-010, US-011, US-012, US-013, US-014 | REQ-013–017, REQ-030, REQ-031, REQ-033, REQ-036 | 8 |

## Coverage

- Requirements: REQ-001 – REQ-044, all covered. **0 gaps.**
- Stories: 30 of 30 assigned. **0 unassigned.**
- Stories with two `comp-` labels: 11 (US-009, US-014, US-018, US-019, US-023, US-024, US-025, US-026, US-027, US-028, US-030).
- ADRs: ADR-001 – ADR-014. One is **Proposed** (ADR-013, hosting region); the rest are Accepted. ADR-010 **supersedes ARCH-016**.
