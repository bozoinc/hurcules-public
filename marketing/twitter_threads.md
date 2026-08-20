# HURCULES Marketing Content — Twitter Threads

## Thread 1: SBOM-for-Agents (Post Day 1, after Dev.to)

```
1/7 Agents load capabilities from GitHub with ZERO verification.

```python
from langchain.tools import load_tool
tool = load_tool("github.com/owner/repo")  # 🤷‍♂️ hope it works
```

No provenance. No license check. No security scan. No approval record.

This is the trust gap. 🧵

2/7 Software solved this a decade ago: **SBOMs** (Software Bill of Materials).
- What shipped, from where, at what version
- Known vulnerabilities (CVEs)
- License posture

Agents need the same — but stronger. A capability *acts*. It calls APIs, spends money, touches data. A confused deputy with your credentials is a supply-chain attack.

3/7 Enter **HURCULES** — the SBOM-for-Agents.

A deterministic compiler that turns any GitHub repo into a **verified, provenance-tracked, human-approved capability package**.

```
GitHub Repo → HURCULES → Verified Capability → Agent Runtime (Hermes, LangChain, CrewAI)
```

No repo code ever executes on your host. Sandboxed. Secrets never leak.

4/7 Proof: HURCULES analyzed **Archon** (1,351 files, agent framework) → 5 verified capabilities:

| Capability | Confidence | Evidence |
|------------|------------|----------|
| Workflow Execution Engine | 0.96 | `src/workflow_engine.py`, `src/executor.py` |
| Adapter System | 0.94 | `src/adapters/base.py`, `src/adapters/registry.py` |
| CLI | 0.95 | `src/cli/main.py`, `src/cli/commands.py` |
| Isolation/Sandboxing | 0.92 | `src/sandbox/docker.py`, `src/sandbox/limits.py` |
| Web Dashboard | 0.90 | `src/dashboard/app.py`, `src/dashboard/routes.py` ```

Every claim cites exact files. Devil's advocate challenges each. Human approves.

5/7 The honest ceiling: **semantic recall ~0.10** vs human gold labels.

We **publish this number**. No marketing spin.

A trust layer that hides its own measurement has already broken the promise it exists to keep. Measured, not promised.

6/7 Three tiers, open-core:
- **Community** ($0, MIT): public repos, full pipeline, honest ceiling — live today
- **Pro** ($79/mo, $500/yr founder): private-repo (air-gapped), Authentik OIDC — gated on shipping
- **Enterprise** ($1,500+/mo): org policies, hosted dashboards, SLA, SBOM export

No money taken until `readiness_report()` clears.

7/7 Try it: `pip install hurcules` → `hurcules ingest --repo <any-repo>`

Read the full piece: [DEVTO_URL_SBOM]
GitHub: github.com/bozoinc/hurcules-public

What's the first repo you'd run this on — and what capability would you need verified?
```

---

## Thread 2: Loops vs Graphs (Post Day 3, after Dev.to)

```
1/7 The agent world is split:

**Camp Loops** (OpenAI Agents SDK, LangGraph): "Agents are loops. Plan→act→observe→repeat."

**Camp Graphs** (Steve Yegge, CrewAI, LangGraph DAGs): "Agents are graphs. Nodes=agents, edges=handoffs."

Both are right. Both are incomplete. 🧵

2/7 Loops get **temporal behavior** right:
- Replanning on failure (ReAct, AdaPlanner)
- Budget enforcement (token caps, cost ceilings)
- Verification gates (process reward models)
- Learning loops (feedback → lessons → suppress)

A loop is a **control structure**: "keep going until condition X."

3/7 Graphs get **structural composition** right:
- Handoffs (peer-to-peer control transfer)
- Parallel execution (swarms, fan-out/fan-in)
- Supervision trees (Erlang/OTP-style restart)
- Provenance (who called whom, with what context)

A graph is a **dependency structure**: "A feeds B, B feeds C, C can restart A."

4/7 **The missing layer neither addresses: Where do the nodes come from?**

Today: find repo → hope it works → wire into graph/loop → pray.

No verification. No SBOM. No attestation. No provenance.

5/7 **HURCULES is the compiler BETWEEN repositories and runtimes.**

```
GitHub Repo → HURCULES → Verified Capability Package → Loop OR Graph Runtime
```

It doesn't care if your runtime is a loop or a graph. It produces **verified capabilities** that work in **either**.

6/7 HURCULES analyzed ITSELF (284 files) → 7 verified capabilities (0.88–0.95 conf).
Honest ceiling: semantic recall ~0.10. Published openly.

MIT core + commercial layer (eval corpus, provenance graph, hosted). The trust layer's credibility IS the product.

7/7 Read: "Loops vs Graphs: Why Agent Architecture Needs Both (and a Compiler Between Them)" [DEVTO_URL_LOOPS]

Try it: `pip install hurcules`

Loops control. Graphs compose. HURCULES verifies. The supply chain needs all three.
```