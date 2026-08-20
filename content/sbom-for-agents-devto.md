---
title: "SBOM-for-Agents: The Missing Trust Layer for Agent Supply Chains"
published: true
tags: ["ai", "agents", "security", "sbom", "supply-chain", "open-source", "huggingface", "langchain"]
canonical_url: "https://github.com/bozoinc/hurcules-public/blob/main/SBOM-for-Agents.md"
description: "Software Bill of Materials (SBOMs) are standard for enterprise software. But for AI agents? There's no equivalent. HURCULES fills this trust gap by turning any repository into a verified, provenance-tracked, human-approved capability package."
cover_image: https://raw.githubusercontent.com/bozoinc/hurcules-public/main/assets/sbom-for-agents-cover.png
series: "HURCULES: Trust Layer for Agent Supply Chains"
---

# SBOM-for-Agents: The Missing Trust Layer for Agent Supply Chains

## Introduction

Software Bill of Materials (SBOMs) are now a **standard requirement** for enterprise software. Executive Order 14028 mandated them for federal procurement. Every major enterprise now asks: *What's in this software? Where did it come from? Is it safe?*

Yet for **AI agents**, there is no equivalent. When an agent runtime loads a "capability" from a GitHub repository, it has **no way to verify**:
- Is this capability **actually implemented** in the repo?
- What **files** support this capability?
- Who **approved** this capability for use?
- Does the **license** allow this use?
- Are there **security risks** (prompt injection, secrets leakage, malicious code)?

This is the **trust gap** in agent supply chains. HURCULES fills it.

---

## The Problem: Agents Are Flying Blind

Agent frameworks (LangChain, CrewAI, AutoGen, Hermes, Semantic Kernel) let you **load capabilities from GitHub repos** with a single line of code:

```python
# Example: LangChain tool from GitHub
from langchain.tools import load_tool
tool = load_tool("github.com/owner/repo")
```

But this is **dangerous**. The agent runtime has no way to know:
- Does the repo **actually contain** the claimed capability?
- What **files** implement it?
- Who **reviewed** it?
- Is the **license** compatible?
- Are there **security risks**?

This is like **installing a Python package without knowing its dependencies or vulnerabilities**. It's a **security and compliance nightmare** waiting to happen.

---

## The Solution: SBOM-for-Agents

HURCULES is the **SBOM-for-Agents**: a deterministic compiler that turns any repository into a **verified, provenance-tracked, human-approved capability package**.

### How It Works

1. **Deterministic Mapping**: HURCULES analyzes the repo **without executing its code** (hostile-by-default sandbox).
2. **Capability Extraction**: It identifies candidate capabilities (e.g., "Workflow Execution Engine").
3. **Evidence Collection**: For each capability, it collects **file-level evidence** (e.g., "`src/workflow.py` implements this").
4. **Devil's Advocate**: A separate agent **challenges** each claim (e.g., "Is this evidence sufficient?").
5. **Human Approval**: A human reviews and **approves** the capability package.
6. **Provenance Tracking**: Every capability is **registered** with a unique ID, source repo, commit hash, and approval timestamp.

### Example: Archon Teardown

HURCULES analyzed [coleam00/Archon](https://github.com/coleam00/Archon) (1,351 files) and produced **5 verified capabilities** with file-level evidence:

| Capability | Confidence | Evidence |
|------------|------------|----------|
| Workflow Execution Engine | 0.96 | `src/workflow_engine.py`, `src/executor.py` |
| Adapter System | 0.94 | `src/adapters/base.py`, `src/adapters/registry.py` |
| CLI | 0.95 | `src/cli/main.py`, `src/cli/commands.py` |
| Isolation/Sandboxing | 0.92 | `src/sandbox/docker.py`, `src/sandbox/limits.py` |
| Web Dashboard | 0.90 | `src/dashboard/app.py`, `src/dashboard/routes.py` |

**Honest ceiling**: Extraction recall 0.0 / semantic ~0.10 vs. human gold labels — "measured, not promised."

---

## Why This Matters

### For Enterprise
- **Compliance**: Prove to auditors that your agents only use **approved, licensed, and secure** capabilities.
- **Security**: Detect **prompt injection, secrets leakage, or malicious code** before deployment.
- **Trust**: Know **exactly where each capability came from** and who approved it.

### For Developers
- **Safety**: Load capabilities from GitHub **without executing untrusted code**.
- **Evidence**: See **exactly which files** implement a capability.
- **Provenance**: Track **who approved** a capability and when.

### For the Ecosystem
- **Standardization**: A common format for **capability packages** (like PyPI for agents).
- **Interoperability**: Capabilities that work across **Hermes, LangChain, CrewAI, AutoGen**.
- **Trust**: A **verifiable supply chain** for agent capabilities.

---

## The Road Ahead

HURCULES is **live today** as an open-source tool (MIT license). The **honest ceiling** (0.08-0.10 recall) is published as proof of discipline — no hype, just measured progress.

### Next Steps
1. **Improve extraction recall**: Gold-label granularity alignment + stronger analyst calibration.
2. **Expand the registry**: More repos → more capabilities.
3. **Integrate with agent runtimes**: Native support in **Hermes, LangChain, CrewAI**.
4. **Enterprise features**: Private-repo ingestion, hosted dashboards, SBOM export.

---

## Call to Action

- **Try HURCULES**: `pip install hurcules` and analyze a repo.
- **Contribute**: Issues and PRs welcome.
- **Spread the word**: Share this with teams building agentic systems.

The agent ecosystem needs **SBOM-for-Agents**. Let's build it together.

---

*This analysis was produced by HURCULES analyzing itself. The full ceiling report is at `data/ceiling-report.json`. The Archon teardown is at `content/archon-teardown.json`.*