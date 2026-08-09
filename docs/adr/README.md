# Architecture Decision Records — HURCULES

ADR = a short, dated, immutable record of a decision. One file per decision.

## When to open an ADR
- A decision changes the public contract, schema, security posture, or dependency set.
- Two reasonable options exist and the chosen one needs a rationale.
- A past decision is revisited or reversed (new ADR supersedes, never edits).

## Format (Copy this header)
```
# ADR-NNNN — Short Title

Status: proposed | accepted | superseded-by ADR-NNNN | rejected
Date: YYYY-MM-DD
Context: what prompted the decision (facts, constraints, options).
Decision: what was chosen, in one paragraph.
Consequences: what this costs, enables, or forbids.
Evidence: link to the run/commit/tests that support the decision.
```

## Numbering
- Increment by 1. Never reuse a number. Superseded ADRs are never deleted.

## Schema/version changes
- Any change to a persisted schema (mapper output, package manifest, registry,
  run-report) increments the schema version and ships a migration — never an
  in-place edit. See SUB-GOALS 2.5.

## Cadence
- CHANGELOG.md is the single source of truth for user-visible changes.
- Baseline tag v0.1.0; semantic versioning thereafter (SemVer 2.0).