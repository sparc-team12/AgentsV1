# Agents

| # | Agent | Input | Output | Status |
|---|-------|-------|--------|--------|
| 01 | [PRD Agent](01-prd-agent/agent.md) | Client conversation | PRD with `REQ-xxx` ids | Done |
| 02 | [User Stories Agent](02-user-stories-agent/agent.md) | PRD | Jira Epics + Stories (traceable) | Done |
| 03 | [Architecture Agent](03-architecture-agent/agent.md) | PRD + Stories | Technical design, `comp-*` labels on stories | Done |
| 08 | Change Request / Bug Triage Agent | Bug or CR in client words | Triage verdict + linked Jira ticket | Not built — next |

Flow: client chats with PRD Agent → PRD → User Stories Agent creates a queryable Jira backlog → Architecture Agent designs against it and stamps `comp-*` back onto the stories → (next) CR/Bug Triage Agent consumes the whole chain.

Read [AGENT-DESIGN-GUIDE.md](AGENT-DESIGN-GUIDE.md) before adding an agent — it covers the traceability chain (`REQ-004 → US-012 → area-checkout → comp-*`), the Jira label schema and why it isn't Components, idempotency, approval gates, and a checklist for designing the next agent.
