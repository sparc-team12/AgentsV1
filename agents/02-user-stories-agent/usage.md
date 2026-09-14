# Using the User Stories Agent

Run it once a PRD in `1. PRD/` is marked `Status: Confirmed`:

> Break down `1. PRD/prd-premium-perfume-ecommerce.md` into user stories in Jira.

It refuses a `Draft` PRD — that gate exists so a team never starts work on scope the client hasn't signed off.

Requires the Atlassian MCP server connected, with permission to create issues in the target project. The agent will ask which project if it can't tell.

It drafts the whole backlog locally first and **waits for your approval** before creating anything in Jira. Review the draft table then — after approval you're editing tickets a team can already see. The draft also lists what it couldn't do: requirements no story covers, NFRs nothing implements, and stories blocked by an open question.

Re-run it after the PRD changes. It reads the PRD Change Log, touches only the requirements that actually moved since the last sync, and matches on `us-`/`req-` labels — so an unchanged PRD produces no new tickets and no edits. Stories for a retired requirement get closed with a reason, never deleted.

## Escalation
Stops and asks when: requirements contradict each other, the Jira project is ambiguous, existing tickets were hand-edited into conflict with the PRD, or the PRD jumped versions with no Change Log explaining what moved.
