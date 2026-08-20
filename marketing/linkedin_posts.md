# HURCULES Marketing Content — LinkedIn Posts

## Post 1: SBOM-for-Agents (Day 2 & 4, enterprise angle)

**Your agent fleet runs on trust that was never verified.**

Ask your security team three questions about the capabilities your agents consume:
1. Which repository, at which commit, did this capability come from?
2. Who approved it for production?
3. Does the license even permit this use?

Most teams get silence. Not because the answers are classified — because nobody asked.

This is **benign neglect**, and it's the default state of the industry. Teams wire GitHub repos into agent runtimes and call it "production." Nothing checked whether the code ran when it shouldn't have, whether a prompt stuffed in a README can hijack the agent's next action, or whether a compliance review ever happened.

**Software learned this lesson with SBOMs. We shouldn't have to learn it twice.**

I built **HURCULES** — the SBOM-for-Agents. A deterministic compiler that turns any repository into a verified, provenance-tracked, human-approved capability package an agent runtime can safely consume.

**Key differentiators:**
- ✅ Deterministic mapping (no LLM hallucination on structure)
- ✅ File-level evidence for every capability claim
- ✅ Devil's advocate adversarial verification
- ✅ Human approval gate with 4-part audit trail
- ✅ Hostile-by-default: never executes repo code on host, secrets never leak
- ✅ Honest ceiling published: semantic recall ~0.10 (measured, not promised)
- ✅ MIT open-core — the trust layer is inspectable by the people it protects

**Enterprise relevance:** Compliance teams can audit the supply chain. Security teams can block unapproved capabilities. Legal teams can verify license posture. All before a capability reaches a runtime.

Read the full analysis: [DEVTO_URL_SBOM]
GitHub: github.com/bozoinc/hurcules-public

#AIAgents #Security #SupplyChain #SBOM #Compliance #OpenSource

---

## Post 2: Loops vs Graphs (Day 4, architecture angle)

**The agent ecosystem is split into two camps. Both are right. Both are incomplete.**

**Camp Loops:** "Agents are loops. Plan → act → observe → repeat." (OpenAI Agents SDK, LangGraph)
**Camp Graphs:** "Agents are graphs. Nodes are agents/tools. Edges are handoffs." (CrewAI, LangGraph DAGs, Steve Yegge)

Loops capture **temporal behavior** — iterative, self-correcting control structures.
Graphs capture **structural composition** — handoffs, parallel execution, supervision trees, provenance.

**The missing layer:** Where do the nodes come from?

Today: find a repo → hope it implements what it claims → wire it in → pray.

No verification layer. No SBOM. No attestation. No provenance.

**HURCULES sits between repositories and runtimes** — a compiler that produces verified capability packages for **either** architecture.

```
GitHub Repo → HURCULES → Verified Capability → Loop Runtime OR Graph Runtime
```

HURCULES analyzed its own repository: 7 verified capabilities, all adversarial-verified.
Honest ceiling: semantic recall ~0.10 — published because a trust layer's credibility IS the product.

Read: "Loops vs Graphs: Why Agent Architecture Needs Both (and a Compiler Between Them)" [DEVTO_URL_LOOPS]

#AgentArchitecture #LangGraph #CrewAI #SoftwareArchitecture #AIEngineering #OpenSource