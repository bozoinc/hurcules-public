# HURCULES

**H**ermes **U**nified **R**epository **C**ompiler **U**tility **L**earning **E**ngine **S**ystem

> Given ONE public GitHub repository URL, HURCULES produces a structured,
> evidence-backed, human-reviewable repository report and a candidate Hermes
> capability package — WITHOUT executing repository code, installing its
> dependencies, accessing secrets, or approving its own output.

## Quickstart

```
pip install hurcules            # or: git clone + pip install -e .
hurcules --version              # 0.7.0
hurcules ingest --repo owner/name   # produces an evidence-backed capability package
```

The free tier is genuinely useful: deterministic repo mapping, capability
extraction with file-level evidence, devil's-advocate verification,
human-approval workflow, and an auditable registry — all on public repos,
all on free model routes. No code from the analyzed repo is ever executed
on your host; secrets never leave the analysis.

## What this project is

A repository-to-capability compiler. The missing layer between external software
(GitHub repos) and agent runtimes (Hermes):

```
GitHub repository → Understanding → Capability extraction → Evidence & provenance
→ Security & licence analysis → Standardised capability package → Compatible agent runtime
```

A **trust layer for agent supply chains**: it turns any repository into a
verified, provenance-tracked, human-approved capability package an agent
runtime can safely consume — the way an SBOM turns software into something a
security team can sign off on.

NOT another agent framework. The system that safely feeds superior capabilities
INTO agent frameworks.

## Core documents

| File | Purpose |
|------|---------|
| [GOAL.md](GOAL.md) | The top-level goal — the consistency contract for the entire project |
| [SUB-GOALS.md](SUB-GOALS.md) | Per-stage sub-goals (Stages 0-10) — measurable definition of done |
| [QIR.md](QIR.md) | Quantum-Inspired Reasoning strategy map — where QIR applies (and where it doesn't) |
| [AGENT-MAP.md](AGENT-MAP.md) | Multi-agent graph architecture — the agent organization |
| [SPEC-SOURCE.txt](SPEC-SOURCE.txt) | The original vision (source of truth) |
| [SECURITY.md](SECURITY.md) | Security posture: hostile-by-default, analysis-yes/execution-no |

## Workflow

This project runs on the Matt Pocock senior-engineer workflow + graph-engineering
multi-agent architecture:

1. **Grill session** — sharpen the idea (product architect's vision)
2. **Wayfinder** — map huge work as decision tickets on the issue tracker
3. **PRD → Issues** — break into independently grabbable issues
4. **Implement** — TDD loop, one issue per session
5. **Code review** — multi-agent review before merge
6. **Commit** — conventional commits, trunk-based

Bugs and errors are first-class citizens: they are filed as GitHub Issues (see
[.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE/)) and flow through the same
workflow as feature work.

## Progress

Waves 0–4 of Update-1 are complete (v0.7.0, 335/335 tests, ~93% coverage):
trust the baseline → trust the model → trust the boundary → trust the loop →
usable & sellable. See [CHANGELOG.md](CHANGELOG.md) and
[SUB-GOALS.md](SUB-GOALS.md) for detail. The full engineering story is in the
[HURCULES self-analysis](data/self-analysis/): HURCULES analyzed its own
repository through the real pipeline and produced 7 verified, evidence-backed
capabilities — dogfooded proof of what it does.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — TDD, determinism-first, stdlib-first,
hostile-by-default. Issues and PRs welcome.

## License

MIT License — see [LICENSE](LICENSE). Copyright (c) 2026 the HURCULES author(s).
