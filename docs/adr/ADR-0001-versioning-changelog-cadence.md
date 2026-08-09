# ADR-0001 — Versioning, ADR, and Changelog Cadence

Status: accepted
Date: 2026-08-09
Supersedes: none
Issue: HURCULES Update-1 Wave 0, item [20]

## Context
HURCULES reaches v0.1.0 baseline today. Every persisted artifact — mapper
output, package manifests, registry entries, and the new run-report ledger —
already carries or will carry a schema version, but there was no documented
process for how the project version, ADRs, and changelog evolve. The pilot
dirty tree (discovery_to_pipeline.py env-routing change + sharkdp__hexyl
artifact) needed a home, and the repo needed a clean tagged baseline before
any further trust work (CI, determinism, cost ledger) could be measured.

## Decision
1. Adopt ADR-as-code: one markdown file per decision under `docs/adr/`,
   Immutable once accepted; supersession via a new ADR, never in-place edit.
   format and numbering rules in `docs/adr/README.md`.
2. Adopt Semantic Versioning (SemVer 2.0.0). Tag the current baseline as
   `v0.1.0`. Pre-1.0: minor = breaking/feature, patch = fix/regression-safe.
3. `CHANGELOG.md` at repo root is the single source of truth for
   user-visible changes, kept under "Unreleased" until a release tag.
4. Schema-versioned artifacts (mapper output, package, registry, run-report)
   must bump their schema version and ship a migration on any shape change —
   never an in-place format edit (reflects SUB-GOALS 2.5).

## Consequences
- Enables reproducible trust work: CI, determinism diffs, and cost ledgers
  all anchor to a stable v0.1.0 tree instead of a moving trunk.
- Every future decision is greppable history rather than tribal knowledge.
- Schema changes become explicit migration work — slower but never silent.

## Evidence
- Baseline tag `v0.1.0` created on the wave-0 housekeeping commit.
- Full suite green: 95/95 pytest (PYTHONPATH=src).