# HURCULES — GOAL (Top-Level)

**HURCULES** = **H**ermes **U**nified **R**epository **C**ompiler **U**tility **L**earning **E**ngine **S**ystem

> Every stage, agent, and line of code in this project exists to serve ONE goal. If work
> does not advance this goal, it does not belong in the project.

## THE GOAL (end-to-end consistency contract)

> **A non-technical person — barely any computer skills, no coding skills — points
> HURCULES at ONE public GitHub repository URL, and receives a self-improving agent
> template capable of producing results as robust, efficient, and capable as a
> senior engineer's — WITHOUT executing the repository's code on the host,
> installing its dependencies, accessing secrets, or needing human engineering.**

The engineering lives INSIDE the template: workflows, validation, recovery, and
guidance are built in, so the human supplies INTENT, not mechanics. The template
self-improves through tested spawns — each use makes it stronger for the next user.

## WHAT "DONE" MEANS (the contract, decomposed)

**INPUT:** one public GitHub repository URL (owner/repo, pinned to an exact commit SHA).

**OUTPUT — the self-improving capability package, containing all of:**
1. Repository map (tree, languages, deps, entry points, tests, CI, docs, licence)
2. Implemented capability candidates (NOT README claims — code/tests-verified)
3. Evidence for every candidate (file + line ranges + confidence)
4. Dependencies and required permissions
5. Licence and security findings (SPDX-aware, hostile-by-default posture)
6. Candidate Hermes capability manifest (ontology-conformant)
7. Evaluation plan (how this capability would be tested)
8. **Operator-facing instructions (novice-safe)** — how a non-technical user
   drives this to senior-quality results
9. **Self-improvement loop** — how tested spawns feed back into template quality

**HARD RESTRICTIONS (never violated):**
1. Do NOT execute the ANALYSED repository's code on the host (it is hostile).
2. Do NOT install its dependencies.
3. Do NOT access secrets.
4. Do NOT auto-approve capabilities — "approved" is a human word (the product owner).
5. Do NOT spawn any agent without the four-part approval: evaluation results +
   capability summary + provenance + live demo.
6. Do NOT run analysed repo code without a real sandbox boundary (it is DATA first).

## FIRST GOLD-STANDARD CASE (to make "works" measurable)

**Repo:** coleam00/Archon (already cloned at ~/projects/Archon).
**Parity bar:** a non-coder, using only the Archon capability template HURCULES
produces, can build a robust agentic harness at Archon's caliber — without
hand-holding. This is Stage 1's gold test case.

## QUALITY BARRIERS (measured, not vibes)

| Metric | Target |
|--------|--------|
| Evidence validity (cited file+lines support the claim) | ≥ 95% |
| Capability precision (capability is materially present) | ≥ 85% |
| Unsupported capability rate (approved w/o evidence) | < 5% |
| Reproducibility (same commit → same structure) | 100% |
| Security (no analysed repo code executes on host) | 100% |
| Provenance (every package identifies source repo+commit) | 100% |
| **Novice usability (non-coder gets senior-quality results)** | **PASS** |
| Self-improvement (spawn → evaluate → package improves) | demonstrated |
| Cost (analysis cost + time recorded per run) | always |

## HOW CONSISTENCY IS ENFORCED

- **Single source of truth:** SPEC-SOURCE.txt + GOAL.md + CONTEXT.md (grill
  decisions D1-D6). No stage may contradict any without a documented ADR.
- **Evidence over prose:** no claim without cited evidence.
- **Deterministic facts first, LLM interpretation second.**
- **Human gates:** nothing is approved, promoted, or spawned without human sign-off.
- **Every stage has sub-goals (SUB-GOALS.md); a stage passes only when its
  sub-goals pass.**

## NON-GOALS (deferred by design — NOT abandoned)

v1 deliberately does NOT: search GitHub autonomously, analyse private repos,
install arbitrary deps, run setup scripts, execute untrusted code on the host
without a sandbox, auto-approve, spawn without human approval, build a public
marketplace, support every agent framework, produce one agent per repo, or claim
generated templates are safe.

These ARE the roadmap after the foundation is trustworthy (Stages 6-10).

## DECISION AUTHORITY (who decides what)

| Decision | Authority |
|----------|-----------|
| What the system must become | the product owner (Founder / Product Architect) |
| What counts as evidence | the product owner + documented policy |
| What qualifies as a superior capability | the product owner (ontology + eval gates) |
| Whether extraction is correct | Independent checks, NOT the extractor |
| Whether a template is safe | Security agent + human approval |
| Whether a licence permits reuse | Licence analysis agent + human sign-off |
| Whether a capability/spawn is approved | the product owner (four-part approval, D4) |
| Whether a failed test can be ignored | Never — fix or document, human-aware |