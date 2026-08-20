# HURCULES Marketing Content — Discord/Slack Messages

## Template (Day 5, all communities — technical, honest, feedback-seeking)

**LangChain Discord #showcase / CrewAI Discord #projects / Hugging Face Discord #agents / AI Engineer Discord #projects / LocalLLaMA Discord #projects:**

Built a tool that verifies agent capabilities from GitHub repos. Honest ceiling: 0.10 semantic recall. Looking for feedback.

**HURCULES** — deterministic compiler: repo → verified capability package (provenance, evidence, human approval, sandboxed). Not a framework — the attestation layer BETWEEN repos and runtimes (Hermes, LangChain, CrewAI, AutoGen).

Analyzed Archon (1,351 files) → 5 verified caps with file evidence. Self-analyzed → 7 caps.

MIT core, open-core. `pip install hurcules`

GitHub: github.com/bozoinc/hurcules-public
Article: [DEVTO_URL_SBOM] / [DEVTO_URL_LOOPS]

Would love feedback on the extraction quality roadmap (R1 targeting 0.20+ recall via gold-label alignment).

---

## Variant for LangChain Discord (more framework-specific)

Built something that might interest this community: **HURCULES** — a verified capability compiler for agent runtimes.

**The problem:** `load_tool("github.com/owner/repo")` gives you zero verification. No provenance, no license check, no security scan, no approval record.

**The solution:** A deterministic compiler that turns any repo into a verified capability package with:
- File-level evidence for every capability
- Devil's advocate adversarial verification
- Human approval gate with audit trail
- Provenance tracking (repo, commit, approver, timestamp)
- Sandboxed — never executes repo code on host
- Honest ceiling published: 0.10 semantic recall

Works with LangChain, CrewAI, Hermes, AutoGen — any runtime that consumes capabilities.

`pip install hurcules` → `hurcules ingest --repo owner/name`

GitHub: github.com/bozoinc/hurcules-public
Dev.to: [DEVTO_URL_SBOM]

Honest feedback welcome, especially on extraction quality (R1 roadmap: gold-label alignment → 0.20+ recall).

---

## Variant for CrewAI Discord

Built **HURCULES** — the missing verification layer for agent capabilities.

Your CrewAI agents load tools from GitHub repos. How do you know:
- The capability is actually implemented?
- What files support it?
- Who approved it?
- The license permits it?
- No prompt injection / secrets leakage?

HURCULES compiles repos into verified capability packages with full provenance + human approval. Sandboxed, never executes repo code on host.

Tested on Archon (1,351 files) → 5 verified capabilities. Self-analysis → 7 caps.

MIT core, honest ceiling: 0.10 recall (published).

`pip install hurcules`

github.com/bozoinc/hurcules-public

Feedback welcome on R1 extraction quality roadmap.