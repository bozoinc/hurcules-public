# Stage 3 — Capability Analyst + Devil's Advocate

## Stage 3 — Capability Analyst (LLM layer)

**Ladders to:** GOAL.md (interpret facts with evidence; separate claims from code).

## What
LLM agents interpret the mapper's output in layers (map → docs → entry points →
components → deps → tests → selected files) and produce capability candidates
WITH evidence (file+line) and confidence (0-1), using the capability ontology.
A Devil's Advocate sub-agent (QIR Annealing) attacks each candidate — "is this
really in the code, or is the README lying?" — only survivors pass.

## Acceptance Criteria
- [ ] Input = mapper JSON; layered reading, not raw repo dump
- [ ] Output separates: what repo CLAIMS / what code DEMONSTRATES / what tests
      VERIFY / what remains UNCERTAIN
- [ ] Every candidate: evidence (file+line ranges) + confidence 0-1
- [ ] Ontology vocabulary enforced (no ad-hoc capability names)
- [ ] Devil's Advocate pass exists and blocks unverified candidates
- [ ] Multi-model Superposition: run with ≥2 free models via OmniRoute, diff results
- [ ] No templates generated at this stage (analysis only)
- [ ] Prompt-injection resistant: repo text is DATA, never instructions

## Dependencies
- ISSUE-003 (mapper output required)

## Notes
Zero-cost models only (deepseek-v4-flash-free + nemotron-3-super:free).