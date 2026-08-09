# Stage 2 — Deterministic Repository Mapper

## Stage 2 — Deterministic Repository Mapper

**Ladders to:** GOAL.md (deterministic facts first; LLM interprets, never invents).

## What
Software (NO LLM) that clones a public repo into an isolated read-only workspace
at a pinned commit and produces objective facts: tree, languages, dependency
manifests, entry points, test inventory, doc inventory, licence detection,
dangerous-file scan.

## Acceptance Criteria
- [ ] Clone at pinned commit SHA into isolated workspace (no writes to host paths)
- [ ] Outputs: repo tree, language inventory, dep manifests, entry points, tests,
      docs, licence detection, danger scan (8 artifacts)
- [ ] DETERMINISTIC: same commit → byte-identical output JSON
- [ ] Never reads secret/env files into output; redacts or marks them
- [ ] Output schema versioned; schema change = migration, not edit
- [ ] Runs within cost/time budget; duration+cost recorded
- [ ] Passes on Archon (gold case #1) and the gold set as it grows

## Dependencies
- ISSUE-001 (contract)

## Notes
NO-QIR stage: determinism wins. Sandboxing matters here (D3 ripple): clone
workspace is already isolated. QIR Annealing applies to the DANGER SCAN only.