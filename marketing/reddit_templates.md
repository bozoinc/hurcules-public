# HURCULES Marketing Content — Reddit Templates

## r/MachineLearning (Day 5, SBOM-for-Agents — research-flavored)

**Title:** [R] SBOM-for-Agents: Verified capability compilation from GitHub repos (honest ceiling: 0.10 recall)

**Body:**
I built HURCULES — a deterministic compiler that turns GitHub repos into verified, provenance-tracked, human-approved capability packages for agent runtimes.

**The problem:** Agent frameworks (LangChain, CrewAI, AutoGen) load capabilities from repos with zero verification. No provenance, no license check, no security scan, no approval record.

**The approach:** 
- Deterministic repo mapping (no LLM)
- LLM analyst proposes capabilities with file citations
- Separate devil's advocate agent challenges every claim
- Compiler builds package, rejects non-conforming
- Human approves → registry entry with full provenance
- All sandboxed, no host code execution

**Results:** Tested on Archon (1,351 files) → 5 verified capabilities with file-level evidence. Self-analysis: 7 capabilities on own repo.

**Honest ceiling:** Semantic recall ~0.10 vs human gold labels. Published openly because a trust layer's credibility is the product.

Open-core (MIT), self-hostable. Paper/code: github.com/bozoinc/hurcules-public

Looking for feedback on the extraction quality roadmap (R1: gold-label alignment → 0.20+ recall).

---

## r/LangChain (Day 5, Loops vs Graphs — architecture-flavored)

**Title:** Loops vs Graphs: Why agent architecture needs both (and a compiler between them)

**Body:**
The ecosystem is split: loops (control) vs graphs (structure). Both are right, both incomplete.

**Loops** = temporal behavior: replanning, budgets, verification gates, learning
**Graphs** = structural composition: handoffs, parallel execution, supervision, provenance

**Neither addresses:** Where do the nodes/capabilities come from?

Today: wire a repo into your graph/loop → pray it works. No verification. No SBOM. No attestation.

I built **HURCULES** — the compiler between repos and runtimes. It produces verified capability packages that work in **either** loops or graphs.

Key insight: The loop/graph is the *consumer*. HURCULES is the *supply chain attestation layer*.

MIT core, honest ceiling published (0.10 recall), self-analyzed on own repo.

Code: github.com/bozoinc/hurcules-public
Article: [DEVTO_URL_LOOPS]

---

## r/LocalLLaMA (Day 5, both — open-source flavored)

**Title:** HURCULES: Open-source repo→verified-capability compiler (honest ceiling: 0.10 recall)

**Body:**
Built a tool that analyzes any GitHub repo and produces verified, evidence-backed capability packages for agent runtimes — without ever executing the repo's code.

**What it does:**
- Maps repo deterministically (file tree, deps, entry points)
- Extracts capabilities with file-level citations
- Devil's advocate challenges every claim
- Human approves → provenance-tracked registry entry
- Sandboxed execution option (Docker, no host FS access)

**Proof:** Analyzed Archon (1,351 files) → 5 capabilities with evidence. Analyzed itself → 7 capabilities.

**Honest ceiling:** 0.10 semantic recall vs human labels. Published because trust layer = credibility.

`pip install hurcules` → `hurcules ingest --repo owner/name`

MIT core, commercial layer for private-repo/auth/dashboards. No money taken until readiness gates clear.

GitHub: github.com/bozoinc/hurcules-public

---

## r/ExperiencedDevs (Day 5, engineering-flavored)

**Title:** HURCULES: The "SBOM for AI agents" — deterministic repo→capability compiler (0.10 recall, published)

**Body:**
Software supply chains have SBOMs. Agent supply chains have... nothing.

When your agent runtime loads a "capability" from a GitHub repo, you have no way to verify:
- Is this capability actually implemented in the repo?
- What files support this capability?
- Who approved this capability for use?
- Does the license allow this use?
- Are there security risks (prompt injection, secrets leakage)?

HURCULES fills this gap. It's a deterministic compiler that turns any repo into a verified, provenance-tracked, human-approved capability package.

**Architecture:**
- Mapper (deterministic, no LLM) → file tree, deps, entry points
- Analyst (LLM) → candidate capabilities with file citations
- Devil's Advocate (separate LLM) → challenges every claim
- Compiler → builds package, rejects non-conforming
- Human approval → registry entry with full provenance
- All sandboxed, no host execution

**Verified on:** Archon (1,351 files, 5 caps), self (284 files, 7 caps), 20+ other repos.

**Honest ceiling:** 0.10 semantic recall. Published because trust layer's credibility IS the product.

MIT core, open-core. `pip install hurcules`

GitHub: github.com/bozoinc/hurcules-public