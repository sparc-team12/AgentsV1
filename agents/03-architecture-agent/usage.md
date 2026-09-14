# Using the Architecture Agent

Run it once a `Status: Confirmed` PRD exists and agent 02 has created the backlog:

> Design the architecture for `1. PRD/prd-premium-perfume-ecommerce.md` against the ACRI backlog.

Requires the Atlassian MCP connection, with permission to edit issues in the target project.

## Before you run it: the NFR gate

On this project the PRD's Non-Functional bucket is empty (**OQ-4**). The agent will still run — it designs module boundaries, the data model, the API surface and assigns `comp-*` labels, all of which follow from the functional requirements — but it will **not** finalise the stack, hosting, scaling, auth or caching. Those come back as ADRs marked `Proposed — blocked by OQ-4`, each naming the answer that would settle it.

To get a complete architecture, answer the NFR questions first and have agent 01 amend the PRD to v1.2 with real `REQ-016+` ids. Provisional answers given in the chat get recorded as **Assumptions**, not requirements — useful to keep moving, not enough to finalise.

Also still open: **OQ-1** (no courier partner) means the order-tracking integration is designed as a seam behind an interface, with no vendor chosen.

## The approval gate

The document is written locally without asking. The Jira label write waits for your explicit approval — review the area→comp map and the per-module story counts first, because after approval you're editing tickets the whole team can see.

The write is additive and conservative: it appends `comp-` to each story's existing labels and fills in the `Components:` line. It never touches story text, acceptance criteria or `Out of Scope`, and it never creates, closes or deletes an issue.

## Re-running

Safe. An unchanged PRD and backlog produce zero edits. After a PRD change the agent scopes from the Change Log and from any story still marked `Components: TBD`, leaving the rest alone. ADRs are append-only — an outdated decision is superseded, never rewritten, so the record of *why* survives.

## Escalation
Stops and asks when: the NFRs are missing (blocks only the NFR-dependent decisions), a constraint and a requirement are incompatible, an integration has no chosen provider, the backlog is out of sync with the PRD, or the `area-*` boundaries won't map to a sane module structure.
