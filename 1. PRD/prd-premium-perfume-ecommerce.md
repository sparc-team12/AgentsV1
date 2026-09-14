# PRD: Premium Perfume E-Commerce Website

**Version:** 1.2 | **Status:** Confirmed | **Last Updated:** 2026-09-13

## Problem Statement
A new venture (no existing offline brand or presence) wants to launch an online store to sell its own-brand premium perfumes across men's, women's, and unisex categories, with free delivery across all of India.

## Goals
- Launch a custom-built e-commerce website to sell own-brand premium perfumes online.
- Offer free delivery nationwide across India.
- Support a v1 catalog of 30 SKUs (10 fragrances x 3 sizes), ~1000 units of stock.
- Enable order placement via Cash-on-Delivery (COD) at launch.

## Non-Goals
- No reselling/distribution of third-party perfume brands.
- No online payment gateway integration in v1 (COD only).
- No customer reviews/ratings in v1.
- No wishlist feature in v1.
- No GST-compliant invoicing.

## Target Users
- **shopper** — premium fragrance buyer (men's, women's, unisex): browses, buys and tracks own-brand perfumes online.
- **admin** — store operator: manages stock levels and fulfils orders.

## Requirements

### Must Have (v1)
- [ ] **REQ-001** — Product catalog with a detail page for each of the 30 SKUs (10 fragrances x 3 sizes)
- [ ] **REQ-002** — Search across the product catalog
- [ ] **REQ-003** — Filter products by fragrance category (men's / women's / unisex)
- [ ] **REQ-004** — Filter products by size
- [ ] **REQ-005** — Filter products by price
- [ ] **REQ-006** — Shopping cart
- [ ] **REQ-007** — Checkout flow with Cash-on-Delivery as the only payment method
- [ ] **REQ-008** — Shopper account creation and login
- [ ] **REQ-009** — Order tracking: shopper can see the status of their order, implemented behind an abstract shipping-provider interface (Accepted — interface only; specific courier/logistics vendor integration deferred to a later phase, see OQ-1 resolution)
- [ ] **REQ-010** — Admin inventory management across ~1000 units of stock
- [ ] **REQ-011** — Admin order management
- [ ] **REQ-012** — Free delivery applied nationwide at checkout, with no delivery fee charged

### Should Have
- [ ] (None specified beyond Must Have — to be revisited)

### Could Have (later)
- [ ] **REQ-013** — Online payment gateway integration
- [ ] **REQ-014** — Customer reviews and ratings
- [ ] **REQ-015** — Wishlist

### Non-Functional
- [ ] **REQ-016** — System supports at least 100 concurrent shoppers at launch without degraded performance
- [ ] **REQ-017** — Page load p95 is under 2.5 seconds
- [ ] **REQ-018** — Platform does not store card/payment data; card processing is delegated entirely to a hosted payment gateway, keeping the platform in PCI SAQ-A scope
- [ ] **REQ-019** — Platform stores customer PII (name, address, order history) required for order fulfilment, with no card/payment data stored (per REQ-018)
- [ ] **REQ-020** — Website meets WCAG 2.1 AA accessibility standard
- [ ] **REQ-021** — Website supports modern evergreen browsers (Chrome, Firefox, Safari, Edge — last 2 versions)
- [ ] **REQ-022** — Website layout is responsive on mobile devices
- [ ] **REQ-023** — Customer and order records are retained for 7 years for tax/accounting record-keeping

## Constraints
- Platform: custom-built website (not Shopify/WooCommerce or similar page-builder platforms)
- Budget: Rs 5,00,000-10,00,000 total
- Timeline: 6 months to launch
- Delivery: free across all of India; specific courier/logistics partner not yet selected
- No GST-compliant invoicing required
- No specific tech stack mandated (open)

## Success Metrics
- Not yet defined by client — see OQ-2.

## Glossary
- **SKU** — one purchasable item: a fragrance in a specific size. 10 fragrances x 3 sizes = 30 SKUs.
- **Fragrance** — a scent product line, sold across three sizes.
- **Fragrance category** — men's, women's, or unisex.
- **COD (Cash-on-Delivery)** — payment collected in cash when the order is delivered; the only payment method in v1.
- **Shopper** — an end customer buying perfume on the site.
- **Free delivery** — no delivery fee charged to the shopper, anywhere in India.
- **PCI SAQ-A** — the lowest PCI-DSS self-assessment tier, applicable when card data is fully handled by a third-party hosted payment gateway and never touches the platform.
- **PII (Personally Identifiable Information)** — customer data stored by the platform: name, address, order history.
- **Shipping-provider interface** — an abstraction layer that lets order tracking work against any courier/logistics vendor, allowing the actual vendor to be selected and plugged in later.

## Open Questions
- ~~**OQ-1** — Which courier/logistics partner will be used for nationwide delivery?~~ (Resolved v1.2 — client deferred vendor selection; REQ-009 to be built behind an abstract shipping-provider interface, courier integration deferred to a later phase)
- **OQ-2** — What success metrics (orders/month, revenue) should be tracked post-launch? (Blocks: none | Owner: client)
- **OQ-3** — No competitor/benchmark sites specified; design/UX direction needs input. (Blocks: none | Owner: client)
- ~~**OQ-4** — Non-functional requirements were never discussed: expected traffic, page-load targets, account security, accessibility, supported browsers/devices, data retention.~~ (Resolved v1.2 — see REQ-016–REQ-023)

## Change Log
| Version | Date | Added | Changed | Retired |
|---|---|---|---|---|
| 1.0 | 2026-09-12 | Initial PRD (unnumbered) | — | — |
| 1.1 | 2026-09-12 | REQ-001-REQ-015, OQ-4, Glossary, persona slugs | Restructured to traceability format; filters split into REQ-003/004/005 and admin panel into REQ-010/011 for atomicity | — |
| 1.2 | 2026-09-13 | REQ-016-REQ-023 (Non-Functional: load, performance, PCI/PII scope, accessibility, browser support, data retention) | REQ-009 reworded to require an abstract shipping-provider interface | OQ-1, OQ-4 resolved |
