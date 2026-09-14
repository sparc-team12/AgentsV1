# SPARC

Agent-driven SDLC — a client idea passes through one agent per specialist role, each handing a document to the next.

**Start here:** [ROADMAP.md](ROADMAP.md) — full agent roster, inputs/outputs, traceability chain, and what to build next. Self-contained enough to hand to a fresh session.

Also: [agents/README.md](agents/README.md) (pipeline index) and [agents/AGENT-DESIGN-GUIDE.md](agents/AGENT-DESIGN-GUIDE.md) (design rules — read before adding an agent).

## Built

1. [PRD Agent](agents/01-prd-agent/agent.md) — interviews a client, outputs a versioned PRD with stable `REQ-xxx` ids ([usage](agents/01-prd-agent/usage.md), [example](agents/01-prd-agent/example.md)).
2. [User Stories Agent](agents/02-user-stories-agent/agent.md) — turns the PRD into Jira Epics and Stories a later agent can query when a change request or bug arrives ([usage](agents/02-user-stories-agent/usage.md)).

## Next

03 Architecture, then 08 Change Request / Bug Triage. See the roadmap for why that order.
