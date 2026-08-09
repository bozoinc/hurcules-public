# Stage 9 — Composition & Spawning (scale)

Parent: ISSUE-009-wayfinder-fog-map.md
Ladders to: GOAL.md — combine validated capabilities into dynamically assembled
sub-agents.

## What
Composition engine: task → capability graph → agent assembly. Assemble MULTIPLE
sub-agents (a fleet) from APPROVED registry capabilities, each carrying
provenance (capabilities + commits), with defined handoff edges (AGENT-MAP).
Strict gates: composition only from approved caps; every assembled agent has
provenance; no spawn without human approval; no agent self-modifies policy.

## Acceptance Criteria (SUB-GOALS Stage 9)
- [ ] 9.1 Composition engine: task → capability graph → agent assembly
- [ ] 9.2 Composition only uses APPROVED registry capabilities
- [ ] 9.3 Each assembled agent carries provenance (caps, commits)
- [ ] 9.4 Multi-agent handoffs follow defined graph patterns (AGENT-MAP)
- [ ] 9.5 No spawn without human approval; no agent self-modifies policy

Exit gate: a composed multi-capability agent passes its evaluation suite (a fleet
spec resolves, all caps approved, provenance traces, and a handoff-validity check
passes) — plus no regressions in Stages 2-8 (87/87 green).

## Dependencies
- ISSUE-006-adapter / Stage 6 adapter (single-agent compose)
- Registry with commit_sha provenance (added 2026-08-06)

## Notes
- Extends compose_agent (single) to a fleet of sub-agents with a DAG of handoffs.
- Deterministic, testable offline (pure assembly; no LLM).