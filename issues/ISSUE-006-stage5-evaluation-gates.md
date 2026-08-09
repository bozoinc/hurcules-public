# Stage 5 — Evidence + Evaluation Gates

## Stage 5 — Evidence & Evaluation Gates

**Ladders to:** GOAL.md (prove quality, don't assert it).

## What
Evaluation harness that tests each candidate package against: success cases,
failure cases, malformed inputs, missing deps, permission restrictions,
prompt-injection attempts, resource abuse, fabricated citations, incompatible
environments. Plus citation-accuracy checker, reproducibility test, cross-model
stability, and the NOVICE PILOT test case (D6).

## Acceptance Criteria
- [ ] Harness runs all 9 attack/validation classes per candidate
- [ ] Verdict format: STATUS + per-check PASS/CONDITIONAL/FAIL
- [ ] Citation checker: do cited lines actually support the claim? (≥95%)
- [ ] Reproducibility: same commit → structurally equivalent (100%)
- [ ] Cross-model: run ≥2 models, diff results, surface divergence
- [ ] Unsupported-capability rate < 5% on gold set
- [ ] NOVICE PILOT: scripted non-technical persona runs the template; PASS =
      senior-quality output without hand-holding (D6)
- [ ] Eval cannot be gamed (Annealing: attack the rubric)

## Dependencies
- ISSUE-005 (compiler output)

## Notes
This is where the parity bar (D2/D6) is actually measured.