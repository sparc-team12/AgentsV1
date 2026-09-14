# Using the PRD Agent

Invoke conversationally — paste `prompt.txt`, then let the client (you, or the real client) chat back and forth. It asks one topic at a time, confirms scope, then outputs the PRD.

Output feeds whatever comes next (ticket breakdown, Jira sync, design). Store the PRD in your doc system — it's the source of truth downstream agents read from.

## Escalation
Agent stops and asks a human when: the ask conflicts with a stated constraint, stakeholders contradict each other, or the client can't answer basic scope questions.
