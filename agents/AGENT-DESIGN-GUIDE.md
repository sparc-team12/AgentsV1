# Agent Design Guide

How this pipeline is built, and how to design the agents that come next.

Audience: anyone joining SPARC who needs to add an agent, or understand why the Jira tickets look the way they do.

---

## 1. The idea

We are modelling how a software company actually works. A client arrives with an idea; it passes through specialists — PM, BA, architect, developer, QA — and each one hands a document to the next. We replace each specialist with an agent.

```
Client idea → [01 PRD Agent] → PRD
                                 ↓
                               [02 User Stories Agent] → Jira Epics + Stories
                                 ↓
                               [03 Architecture Agent] → technical design
                                 ↓
                               [04+ Build / QA agents] → code
```

An agent owns exactly one transformation, has one input document and one output document, and does not do the next agent's job. This is the single most important rule. An agent that "also does a bit of architecture" produces work the architecture agent cannot cleanly override, and the pipeline stops being composable.

## 2. The problem this guide exists to solve

A pipeline that only runs forwards is a one-shot document generator. Real projects run **backwards** constantly:

> "The client wants COD orders to allow partial cancellation." — which story is that? What else breaks?
>
> "Bug: cart total is wrong when a filter is applied." — which story's acceptance criteria does this violate?

A change request or bug arrives months later, referencing a *feature*, never a ticket id. A future agent has to find the right story, or it will work blind — patching code with no idea which requirement it was meant to satisfy, and no idea what else depends on it.

So the backlog must be **queryable by machine**, not merely readable by humans. Everything below follows from that.

## 3. The traceability chain

One unbroken chain of stable ids, from the client's sentence down to the code:

```
REQ-004  (PRD requirement)
   └── US-012  (user story, Jira SCRUM-45)
          └── area-checkout  (feature area → Epic → later, a code module)
                 └── comp-payment-service  (added once architecture exists)
```

Given any link, an agent can walk to the others. That is the whole design.

**Ids are permanent.** `REQ-004` means the same thing forever. Renumbering breaks every reference in every document, ticket and commit that already points at it — including ones the agent cannot see. This is why the PRD agent numbers requirements even though a human reader does not need the numbers.

**Requirements must be atomic**, or the chain frays at the first link: if `REQ-004` means "filters by category, size and price", a change request about price filtering lands on an id that is two-thirds about something else, and the agent cannot tell what it may safely touch. One requirement = one independently verifiable capability.

Note `US-012` exists *alongside* the Jira key `SCRUM-45`. Jira keys are assigned by Jira and change if a project is migrated or an issue moved; our own id does not.

## 4. The PRD is a living document

The first version of this pipeline assumed the PRD gets written once. Real clients change their minds in week six, and that is where naive pipelines break: a second interview produces a fresh document, ids shift by one, and every `req-` label in Jira now points at the wrong requirement.

Four mechanisms prevent that:

**Version + Status.** The PRD header carries `Version`, `Status` (`Draft` / `Confirmed`) and `Last Updated`. Downstream agents refuse to build a backlog from a `Draft` — otherwise a team starts working on scope the client has not signed off. An amendment drops the status back to `Draft` until re-confirmed.

**Amend, never re-create.** An existing requirement keeps its id when reworded. A new one takes the next free number even if it belongs in the middle of the document. One product has exactly one PRD.

**Retire, never delete.** A dropped requirement is struck through with a reason, not removed. Its stories get *closed*, not deleted. Six months later someone asks why the wishlist never shipped, and the answer is still in the document and the ticket history.

**Change Log.** Each version records which ids were Added / Changed / Retired. This is what makes re-syncing safe: the stories agent acts only on ids named in the rows since the version it last synced, and leaves everything else alone. Without it, a re-sync has to blind-diff the whole PRD and will happily flatten a ticket a human refined by hand last week.

## 5. Vocabulary is part of the contract

The PRD's **Glossary** fixes one canonical spelling per domain term, and every downstream document uses it.

This looks like style pedantry and is not. Half the retrieval design rests on `text ~ "..."` matching inside a filtered set. If the PRD says "fragrance family", a story says "category", and the client's bug report says "scent type", nothing matches anything and the agent handling that bug concludes no story exists. Vocabulary drift breaks machine retrieval silently — there is no error, just a miss.

The same applies to **persona slugs**. The PRD defines `parent`, `tutor`, `admin`; stories reuse them verbatim as the "As a ..." role rather than inventing "guardian" or "teacher".

## 6. Why labels, not Jira Components

The obvious way to tag a story by feature area is Jira's **Components** field. We don't, and this was a correction made after checking the API rather than assuming:

- Jira **rejects a component name that doesn't already exist** in the project, and the whole issue-create call fails with it. Someone must pre-create components in project settings by hand.
- There is no MCP tool to create a component, so the agent cannot self-heal.
- **Labels are free-form** — writing `area-checkout` creates it on the spot.
- Labels are exact-matched in JQL (`labels = req-004`), so they work as a reliable join key.

So: **labels are the primary axis; components are optional decoration** set only when they already exist.

Two constraints worth memorising: Jira labels **cannot contain spaces** (use lowercase kebab-case), and every Jira MCP call needs a `cloudId`, resolved once per run via `getAccessibleAtlassianResources`.

## 7. The label schema

Every story carries exactly four kinds of label. Nothing else, or the scheme stops being predictable.

| Label | Example | Answers |
|---|---|---|
| `us-<nnn>` | `us-012` | Which story is this? |
| `req-<nnn>` | `req-004` | Which PRD requirement does it implement? (repeatable) |
| `area-<slug>` | `area-checkout` | Which feature area / Epic? |
| `phase-<bucket>` | `phase-v1` | Is it in scope now? |

Which makes every lookup a one-line query:

| Situation | JQL |
|---|---|
| Bug in checkout mentioning "coupon" | `project = X AND labels = area-checkout AND text ~ "coupon"` |
| CR against a PRD requirement | `project = X AND labels = req-004` |
| Fetch one known story | `project = X AND labels = us-012` |
| Everything in v1 scope | `project = X AND labels = phase-v1` |

Structured filters beat full-text search. `text ~ "checkout"` also matches every story that merely *mentions* checkout; `labels = area-checkout` matches exactly the ones that *are* checkout. Text search is the fallback **within** a filtered set, never the primary lookup.

## 8. The story description template

Fixed headings, because a future agent parses them:

```markdown
**Story**
As a <persona-slug>, I want <capability>, so that <benefit>.

**Acceptance Criteria**
1. Given <context>, when <action>, then <observable outcome>.

**Traceability**
- Story-Id: US-012
- PRD-Ref: REQ-004, REQ-009
- PRD-Doc: 1. PRD/prd-<name>.md @ v1.2
- Area: checkout
- Depends-On: US-003
- Components: TBD (set by architecture agent)

**Out of Scope**
- <what this story deliberately does not cover>
```

Two things carry most of the downstream weight:

**Acceptance criteria in Given/When/Then.** A bug report describes behaviour, so behaviour is what we match it against: the agent finds the AC the bug violates, and that identifies the story. Criteria written as implementation notes ("validate the cart in the service layer") are unmatchable. Unhappy paths matter most — out-of-stock, invalid input, network failure — because that is where bugs actually live.

**`Out of Scope`.** It lets a future agent tell a *bug* ("this should work and doesn't") from a *change request* ("this never worked, and now we want it"). Without it, every CR looks like a bug.

## 9. Non-functional requirements

NFRs — performance, security, compliance, accessibility — get `REQ-` ids like everything else, because the architecture agent has to trace to them and QA has to test them. But they rarely become stories of their own: one performance requirement constrains twenty stories at once.

So an NFR is normally carried as an extra `req-` label **and an acceptance criterion** on each story it constrains. It becomes a story in its own right only when it implies standalone work — rate limiting, audit logging, a consent banner — filed under an `area-platform` Epic.

Either way, every NFR id must end up referenced by at least one story, and the stories agent reports the ones that aren't. An NFR nobody implemented is the classic way a project passes every ticket and still fails acceptance.

Clients almost never volunteer NFRs, which is why the PRD agent asks for them explicitly rather than waiting.

## 10. Idempotency

The PRD will change, and the agent will be re-run. A re-run against an unchanged PRD must create **zero** new issues and make zero edits.

So the agent searches before it writes — `labels = us-012`, `labels = req-004` — and edits in place when it finds a match. This is why the dedupe key must be an exact-match label and not a text search of the description: `description ~ "REQ-004"` is tokenised and fuzzy, and a near-miss silently duplicates the backlog.

Scope matters as much as dedupe. A re-sync acts only on the ids the Change Log says moved (section 4); everything else is left alone. And if a human has hand-edited a story so it now conflicts with the PRD, report the difference and stop — don't overwrite someone's work to satisfy a document.

## 11. Human approval gates

Writing to Jira is visible to a whole team and awkward to reverse. The agent therefore drafts the entire backlog to a local file, shows a summary, and **waits for explicit approval** before the first `createJiraIssue`.

The general rule for any agent in this pipeline: *local and reversible, go ahead; shared and hard to undo, ask first.*

At that gate the agent also reports what it could not do: requirements no story covers, stories tracing to no requirement, NFRs nothing implements, and stories blocked by an open question. An agent that hides its gaps is worse than one that has them.

On blocking: an open question names the requirements it blocks (`Blocks: REQ-004`), so the agent skips exactly those stories and builds the rest. Blocking the entire run on one unanswered question is how a pipeline becomes useless in practice.

## 12. Source of truth

Jira is the source of truth for stories. The local `2. User Stories/story-index.md` is a **cache** for fast lookup without a round trip, and it goes stale the moment someone edits a ticket in the browser. Any agent relying on it for a decision must verify against Jira first.

Same rule one step up: the PRD is the source of truth for requirements; the stories are a derived view.

## 13. Checklist for designing the next agent

Each agent in this pipeline should answer all of these before it gets written:

1. **One transformation.** What single document goes in, what single artifact comes out? If you can't say it in one line, it's two agents.
2. **What does it *not* do?** Write the exclusions into the prompt explicitly — this is what stops agents bleeding into each other.
3. **How does its output get found later?** Which ids does it inherit, which does it mint, and what query retrieves them? (The architecture agent, for instance, inherits `area-*` and mints `comp-*`, and must write `comp-*` back onto the stories so the chain closes.)
4. **What happens on the second run?** What's the dedupe key, and what tells it which parts actually changed?
5. **What happens when its input changes underneath it?** Versioned input, changed ids, retired ids — all three need an answer.
6. **Where's the approval gate?** Anything shared or irreversible needs one. Nothing is ever deleted; things are closed or retired.
7. **When does it escalate to a human?** Contradictions, ambiguity, missing permissions — and it blocks the narrowest slice it can, not the whole run.
8. **Verify the tool schemas before writing the prompt.** The Components mistake in section 6 was caught this way. Assumptions about an external API belong in the "check first" pile, not the prompt.

## 14. File layout

```
.claude/agents/<name>.md          the executable agent (frontmatter + prompt)
agents/<nn>-<name>/agent.md       human-readable spec for the same agent
agents/README.md                  pipeline index
agents/AGENT-DESIGN-GUIDE.md      this document
1. PRD/                           PRD agent output
2. User Stories/                  backlog draft + story index cache
```
