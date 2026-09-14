# Jira Story Lifecycle

What happens to one story, end to end, and why the pipeline is built this way. Two different "phase" concepts show up below — don't conflate them: the **pipeline stage** (which agent has touched the story) and the **scope phase** (the `phase-v1`/`phase-should`/`phase-later` label, i.e. *when* it ships).

## Pipeline stages (what a story passes through)

```
0. PRD            REQ-xxx minted, Status: Confirmed          (01 PRD Agent)
1. Draft backlog  backlog-draft.md — local file, not in Jira (02 User Stories Agent)
2. Approval gate  human reviews the draft table              ← nothing exists in Jira yet
3. Created        Epic + Story in Jira, labels:
                  us-<nnn> req-<nnn> area-<slug> phase-<bucket>
4. Architected    comp-<module> label + Components: line stamped on (03 Architecture Agent)
5. Approval gate  human approves the label write-back         ← same story, no new fields invented
6. Implemented    branch/PR referencing US-<nnn>              (05, not yet built)
7. Reviewed       PR checked against the story's AC + module boundary (06, not yet built)
8. Tested         one test per Acceptance Criterion            (07, not yet built)
9. Released       shipped, changelog cites REQ-/US- ids         (09, not yet built)

   ↺ Change Request / Bug Triage (08, not yet built) re-enters at any point —
     it queries the labels to find the story, then routes back to 01/02/05.
```

Stages 0–4 are built and have run on this project (ACRI project, 21 stories). Stages 6–9 don't exist yet — see `ROADMAP.md` for build order.

Each stage is owned by exactly one agent, and each agent mints exactly one new label/field and never touches what a previous stage wrote (labels only ever get *appended to*, never replaced). That's what "one agent = one transformation" buys you: you can always point at a label and know which stage produced it.

## Scope phase (the other kind of "phase")

`phase-v1` / `phase-should` / `phase-later` is a priority label set once at story creation (stage 3), independent of pipeline progress. It answers "is this in scope *now*", not "how far along is it". Example from this backlog: `US-013` (online payment) is `phase: later` — it exists, is architected (has a `comp-checkout` label), but isn't scheduled for v1 build.

## Why this makes the plan efficient

- **Single-writer labels, no merge conflicts.** `us-`/`req-`/`area-` are written once by agent 02 and never touched again; `comp-` is written once by agent 03. No two agents ever contend for the same field, so re-running one stage can never corrupt another's output.
- **Idempotent re-runs cost nothing on unchanged input.** Every write step searches before creating. Re-invoking the whole pipeline against an unchanged PRD produces zero new tickets and zero edits — so agents can be re-run liberally instead of being treated as one-shot, fragile operations.
- **Approval gates sit only at irreversible/shared writes.** Drafting (backlog-draft.md, architecture.md) is unrestricted and local; only the Jira write and any future git/prod write need a human nod. That keeps iteration fast without risking a whole-team-visible mistake.
- **Retrieval is a label query, not a document search.** "Bug in checkout mentioning coupon" is `labels = area-checkout AND text ~ "coupon"`; "blast radius of a module" is `labels = comp-payment-service`. Triage (stage 08) will run in JQL time, not by reading every ticket.
- **Blocking is scoped to the narrowest slice.** When a requirement was missing (OQ-4, OQ-1), the affected ADRs/stories were marked blocked while everything else proceeded — the whole pipeline never stalled on one open question.
- **The scope-phase label lets architecture run ahead of build priority.** `phase-later` stories (e.g. online payment) still get designed and labelled now, so when they *do* get pulled into a sprint there's no re-discovery — just a status change.
