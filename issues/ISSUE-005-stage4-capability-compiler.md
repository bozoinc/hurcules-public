# Stage 4 — Capability Schema + Compiler

## Stage 4 — Capability Schema + Compiler (software)

**Ladders to:** GOAL.md (standard, validated, evidence-backed packages).

## What
Deterministic software that converts analyst output into the standard package
and REJECTS invalid packages. Schema: manifest.yaml, provenance.yaml, role.md,
instructions.md, tools/, workflows/, schemas/, evaluations/, security/
(permissions.yaml, threat-model.md, findings.json), licensing/, evidence/source-map.json.
PLUS operator-facing instructions (novice-safe) and the self-improvement loop
placeholder (D5/D6).

## Acceptance Criteria
- [ ] Package schema defined + versioned (JSON Schema)
- [ ] Compiler validates: schema validity, referenced files exist, cited line
      ranges exist, deps match manifests, required fields present, capability IDs
      unique, permissions use approved values, eval commands permitted, no secrets
- [ ] REJECTS incomplete/contradictory packages — no silent repair
- [ ] Deterministic given same analyst output
- [ ] Registry entry format (capability_id, version, status=candidate)
- [ ] Operator-facing instructions section present (novice-safe, D6)
- [ ] Self-improvement loop hook present (D5): spawn-test outcomes feed back

## Dependencies
- ISSUE-004 (analyst output)

## Notes
NO-QIR in validation logic. Entanglement: schema changes must map consumers
(registry, adapter, gold files) in the PR.