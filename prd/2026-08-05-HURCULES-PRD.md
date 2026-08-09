# HURCULES — Product Requirements Document

Date: 2026-08-05 | Status: DRAFT (awaiting the product owner confirmation)
Source: grill session (CONTEXT.md D1-D6) + SPEC-SOURCE.txt + GOAL.md

## Problem Statement

A non-technical person cannot turn a useful GitHub repository into a safe,
reusable agent capability. Today that requires: understanding the repo's
architecture, separating README claims from real code, identifying reusable
parts, analysing dependencies/permissions/licences, rewriting concepts as
skills/workflows, connecting to an agent runtime, testing it, and keeping the
result safe to run. That is a senior-engineer's job — and only they can do it.

HURCULES removes that barrier: point it at a repo, receive a self-improving,
novice-safe agent template that produces results at the quality of the repo's
own engineering — no coding required to operate it.

## User Story (concrete persona)

> **Marcus**, a tech-curious entrepreneur with no coding background. He runs a
> service business, uses AI tools daily for marketing and drafting, and wants to
> build a custom AI assistant for his operations — but hiring engineers is out
> of budget and he can't write code. He does not know what a GitHub repository
> is, or what an "agent harness" is. He wants to say, in plain words, what he
> needs — and get reliable, senior-quality output.

- When Marcus (or any non-technical user) points HURCULES at a repository,
  the system returns a template he can operate with plain-language intent.
- He does not read code, write code, or touch commands beyond clicking/typing.
- The template handles the engineering internally (workflows, checks, recovery).
- The result he gets is as robust as what a hired engineer would produce.

First internal user: **Hermes + the product owner** (dogfood). The non-technical bar is the
north star, but we validate quality gates ourselves first.

## The One Sentence Product Promise

> Give HURCULES a public GitHub repository and receive a traceable, reviewable,
> self-improving agent capability package a non-technical person can operate to
> get senior-engineer-quality results.

## Acceptance Criteria (measurable, from GOAL.md)

1. Evidence validity ≥ 95% (cited file+line supports the claim)
2. Capability precision ≥ 85% (capability is materially present)
3. Unsupported capability rate < 5% (approved without evidence)
4. Reproducibility: same commit → structurally equivalent result (100%)
5. Security: no analysed repo code executes on host without a sandbox (100%)
6. Provenance: every package identifies source repo + commit (100%)
7. **Novice usability: a non-coder, using only the template, produces
   senior-quality results (PASS)**
8. Self-improvement: spawn → evaluate → package improves (demonstrated)
9. Cost + duration recorded for every run (always)

## Non-Goals (v1 scope — deferred, not abandoned)

- Autonomous GitHub-wide discovery
- Private repository analysis
- Auto-installing arbitrary dependencies
- Running setup scripts
- Executing untrusted code on host without a real sandbox
- Auto-approving capabilities/spawns (human approval always required)
- Public marketplace / multi-tenant accounts / billing (Stage 10)
- Supporting every agent framework (Hermes first; others later)
- Producing one agent per repository (quality over quantity)
- Claiming generated templates are automatically safe

## Technical Notes (seams + architecture)

### Pipeline (Stage 0 → 6 core)
```
Contract → Gold-set → Deterministic Mapper → Capability Analyst (+ Devil's Advocate)
→ Compiler (validates) → Evidence Checker → Security/Licence Auditor
→ Evaluation Harness → Registry Gate (human) → Hermes Adapter/Spawner
```
Full multi-agent graph: see AGENT-MAP.md (A1-A9).

### Spawn policy (contract overrides — CONTEXT.md)
- Spawn-from-day-one, sandboxed, human-approved (D3).
- "Approved" = evaluation results + capability summary + provenance + live demo (D4).
- Spawning is TEST-CENTRIC: every spawn is evaluated and the results feed back
  into template quality (D5). This is what makes the template self-improving.
- Sandbox is a Stage 1-2 dependency, NOT Stage 7 (any spawn needs isolation).

### Non-technical usability (the load-bearing requirement)
- Templates include operator-facing instructions (novice-safe).
- Evaluation harness includes a "novice pilot" test case (non-technical persona).
- The self-improvement loop is what lets the template close the gap over time.

### QIR quantum strategies
- Applied only where they add value (QIR.md): Superposition for multi-model
  analysis and capability candidates; Entanglement before any schema/contract
  change; Annealing for the Devil's Advocate and sandbox red-team.
- Deterministic stages (Mapper, Compiler validation) are NO-QIR.

### Model/Cost constraints
- Zero-cost free models only (deepseek-v4-flash-free, nemotron-3-super:free,
  local llama-server) unless the product owner explicitly approves paid.
- Superposition bounded: max 3 candidates / 2-3 models per analysis.

### Security posture (SECURITY.md)
- Every repo treated as hostile until proven otherwise.
- Analysis allowed; execution denied by default; permission explicit.
- OpenAI/agentic threat guidance applies; SPDX/SLSA for supply-chain.

## Risks & Open Implementation Decisions
- Sandbox depth (full container vs worktree-only vs permissive-local) — decide in issues phase.
- Gold-standard label specifics — Stage 1 detail.
- Capability ontology vocabulary finalization — Stage 1-3 detail.
- Whether novice pilot is automated or scripted persona — Stage 5 detail.

## Next Step
Upon the product owner confirmation → `/to-issues` (break into independently grabbable issues,
write to issues/, file to GitHub, ready for `/implement` per issue).