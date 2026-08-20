---
title: "Loops vs Graphs: Why Agent Architecture Needs Both (and a Compiler Between Them)"
published: true
tags: ["ai", "agents", "architecture", "langgraph", "langchain", "crewai", "openai", "software-architecture"]
canonical_url: "https://github.com/bozoinc/hurcules-public/blob/main/Loops-vs-Graphs.md"
description: "The agent ecosystem is split into loops and graphs camps. Both are right. Both are incomplete. HURCULES is the compiler that sits between repositories and runtimes, producing verified capabilities for either architecture."
cover_image: https://raw.githubusercontent.com/bozoinc/hurcules-public/main/assets/loops-vs-graphs-cover.png
series: "HURCULES: Trust Layer for Agent Supply Chains"
---

# Loops vs Graphs: Why Agent Architecture Needs Both (and a Compiler Between Them)

## The False Dichotomy

The agent ecosystem is split into two camps:

**Camp Loops** (Boris Cherny, OpenAI Agents SDK, LangGraph):
> "Agents are loops. Plan → act → observe → repeat. The loop is the atomic unit."

**Camp Graphs** (Steve Yegge, Gas Town, LangGraph DAGs, CrewAI):
> "Agents are graphs. Nodes are agents/tools. Edges are handoffs. The graph is the architecture."

**Both are right. Both are incomplete.**

---

## What Loops Get Right

Loops capture **temporal behavior** — the iterative, self-correcting nature of agent work:
- **Replanning on failure** (AdaPlanner, ReAct)
- **Budget enforcement** (token caps, step limits, cost ceilings)
- **Verification gates** (process reward models, extraction floors)
- **Learning loops** (feedback → lessons → advisory → suppress)

A loop is a **control structure**. It says: *keep going until condition X*.

---

## What Graphs Get Right

Graphs capture **structural composition** — how capabilities connect:
- **Handoffs** (peer-to-peer control transfer)
- **Parallel execution** (swarms, polecats, fan-out/fan-in)
- **Supervision trees** (Erlang/OTP-style restart strategies)
- **Provenance** (who called whom, with what context)

A graph is a **dependency structure**. It says: *A feeds B, B feeds C, C can restart A*.

---

## The Missing Layer: A Compiler Between Repos and Runtime

Here's what neither camp addresses: **Where do the nodes come from?**

Today:
- You find a repo on GitHub
- You hope it implements what it claims
- You wire it into your graph/loop
- You pray it works

**There's no verification layer.** No SBOM. No attestation. No provenance.

---

## HURCULES: The Compiler Between Repos and Runtime

HURCULES sits **between the repository and the agent runtime**:

```
GitHub Repository → HURCULES → Verified Capability Package → Agent Runtime (Loop or Graph)
```

It doesn't care if your runtime is a **loop** or a **graph**. It produces **verified capabilities** that work in **either**.

### What HURCULES Compiles

| Input | Output |
|-------|--------|
| Raw repo (any language) | Deterministic map (file tree, deps, entry points) |
| Map + LLM analyst | Candidate capabilities with file citations |
| Candidates + Devil's Advocate | Challenged, evidence-backed capabilities |
| Challenged + Human approval | **Verified capability package** (registry entry) |

### The Package Contains
- **Capability spec** (name, description, interface)
- **File-level evidence** (exact files implementing each claim)
- **Provenance** (source repo, commit hash, timestamp)
- **Approval trail** (who approved, when, what they saw)
- **License classification** (permissive/copyleft/proprietary/unknown)
- **Security scan** (secrets, injection patterns, malicious patterns)

---

## Loops Need Verified Nodes

A loop that runs on **unverified capabilities** is a liability:
- The loop replans, but the capability was never real
- The budget enforces cost, but the capability is malicious
- The verification gate passes, but the evidence was hallucinated

**HURCULES gives loops verified nodes.** The loop becomes a **control structure over attested capabilities**.

---

## Graphs Need Verified Edges

A graph with **unverified nodes** is a supply chain attack waiting to happen:
- Node A hands off to Node B
- Node B was never verified
- The edge carries malicious context
- Supervision restarts Node B, but the capability is still broken

**HURCULES gives graphs verified nodes with provenance.** The graph becomes a **composition of attested capabilities**.

---

## The Architecture: Compiler + Runtime

```
┌─────────────────────────────────────────────────────────────┐
│                     AGENT RUNTIME                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │    Loop     │  │    Graph    │  │  Hybrid     │          │
│  │  (control)  │  │ (structure) │  │  (both)     │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
              ┌─────────────────────────┐
              │   VERIFIED CAPABILITY   │
              │       REGISTRY          │
              │  (HURCULES OUTPUT)      │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │      HURCULES           │
              │  (REPO → CAPABILITY)    │
              │  map → analyst →        │
              │  advocate → consolidate │
              │  → compile → approve    │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │    GITHUB REPOSITORIES  │
              │   (raw, untrusted)      │
              └─────────────────────────┘
```

---

## Why This Changes Everything

### For Loop Builders
- Your loop **never runs on hallucinated capabilities**
- The **extraction floor** catches empty/unparseable output
- The **devil's advocate** challenges every claim
- **Cost routing** picks the right model tier for the job

### For Graph Builders
- Your nodes have **provenance** (source, commit, approver)
- Your edges carry **verified context** (not raw LLM output)
- Your supervision tree can **audit the capability**, not just the process

### For Enterprise
- **SBOM-for-Agents** is now real
- Compliance teams can **audit the supply chain**
- Security teams can **block unapproved capabilities**
- Legal teams can **verify license compliance**

---

## The Honest Ceiling

We don't claim perfection. HURCULES's **semantic recall is ~0.10** against human gold labels.

We **publish this number**. Every release.

Because the trust layer **must be honest about its own limits**. A trust layer that lies about its recall is worse than no trust layer.

---

## What's Next

1. **R1**: Extraction quality lift (gold-label alignment → recall ~0.20+)
2. **R2**: Private-repo ingestion + Authentik OIDC (Pro tier)
3. **R3**: Hosted dashboards + SBOM export (Enterprise tier)
4. **Registry growth**: 26 → 60+ verified capabilities
5. **Runtime integrations**: Native Hermes, LangChain, CrewAI support

---

## The Thesis

**The agent ecosystem doesn't need another loop framework or another graph framework.**

It needs a **verified capability supply chain**.

HURCULES is that supply chain. Loops and graphs are the consumers.

**Try it**: `pip install hurcules` → `hurcules ingest --repo <any-repo>`

The ceiling report is at `data/ceiling-report.json`. The evidence is in every package.

*Measured, not promised.*