# The SBOM for Agents: Why Your Agent Fleet Needs a Bill of Materials

>*A category-defining piece by the HURCULES project — the trust layer for agent supply chains. No hype, honest numbers, publishable today.*

---

## 1. Most agent fleets run on trust that was never verified

Ask your security team three questions about the code your agents run on: which repository did this capability come from, and at which commit? Who approved it for production? Does the license even permit you to use it?

Most teams get silence — not because the answers are classified, but because nobody asked. Agent capabilities are assembled the way the internet was assembled in 1999: enthusiastically, with the security posture decided after the fact, if ever.

This is **benign neglect**, and it is the default state of the industry. Teams pick a repo, wire it into a runtime, and call the agent "production." Nothing checked whether the code ran when it shouldn't have, whether a prompt stuffed inside a README can hijack the agent's next action, or whether a compliance review ever happened. The word for software consumed this way is not "integrated." It is **unevaluated**. Software already learned this lesson; we shouldn't have to learn it twice.

## 2. Software got an SBOM. Agents need a bill of materials too.

A decade of supply-chain attacks pushed the industry to a blunt, working answer: the **Software Bill of Materials**. An SBOM makes three things true about software you consume:

- **Provenance** — what shipped, from where, at which version. No magic blobs; an identifiable record.
- **Known exposure** — inventories checked against vulnerability feeds. "Are we exposed to CVE-X?" is answered in minutes, not months.
- **License posture** — what you may legally distribute or run, before legal finds out the hard way.

The same logic applies to agents — and more strongly, because the unit being inventoried is a capability that *acts*, not bytes sitting inertly on disk.

| What SBOMs solved for software | The agent-capability equivalent |
|---|---|
| Provenance of a dependency | Verified source: repo + commit + extraction evidence, not "cloned from somewhere" |
| Known vulnerabilities / CVEs | Prompt-injection exposure and embedded hostile behavior in repo code |
| License posture | License posture — unchanged, and mostly ignored today |
| *(added by agents)* | **Human approval**: who at your org signed off on this capability? |

That last row is the difference that matters. A library cannot call your billing API by itself; an agent capability *is* the action surface. So an agent's bill of materials is incomplete without an approval chain — consuming a capability is closer to hiring a contractor than importing a package.

## 3. Why this matters more for agents, not less

A wrong dependency is a bug in your application. A wrong capability is an **autonomous actor with its own security posture**.

Agents call tools, spend money, touch data. Give an agent a capability you never vetted, and you've deputized unknown code to act on your behalf. The classic failure is the **confused deputy**: a privileged actor (your agent, carrying your credentials) executing instructions from an untrusted source without checking who left them. Put a malicious or oblivious prompt inside a capability's own documentation, and the agent will read its *own supply chain* as instructions. That is **tool poisoning** — no break-in required, only that you added their artifact to your fleet.

An SBOM doesn't stop a confused deputy from being confused. But SBOM-plus-approval-gate changes the math: "who verified this, who approved it, what did it do in testing?" becomes answerable *before* the capability reaches a runtime. Today that question isn't just unanswered — it's unasked.

## 4. The answer is an attestation layer, not another framework

That's where HURCULES sits — not another agent framework. Frameworks, LangGraph and Archon and the like, are the *destination* for governed capabilities. HURCULES is the **compile-and-attest layer between repositories and runtimes**: a deterministic compiler that turns any GitHub repo into a verified, provenance-tracked, human-approved capability package an agent runtime can safely consume.

Three behaviors are the whole product:

- **Evidence-backed extraction.** Every capability carries file-level evidence and a provenance chain: which repo, which commit, what was examined. Deterministic — same repo in, same capabilities out.
- **Human approval, four-part audit trail.** Nothing is registry-listed until a person can see where it came from, what it does, and who signed off. The D4 artifact makes the call auditable: who, what, when, why.
- **Hostile-by-default execution boundary.** HURCULES never executes repo code on your host. Everything runs sandbox-gated; secrets never leave; only file and path names surface. A prompt-injection battery is part of the pipeline, not an afterthought.

The proof is the dogfood: HURCULES analyzed its *own* repository and produced 7 verified capabilities from it. The non-coder path is machine-tested, not aspirational. MIT open-core, so the trust layer is inspectable by the people it exists to protect.

## 5. The honest note: this field is early, and we publish our ceiling

Category-creation writing usually claims the future as if it were the present. We're breaking that convention on purpose.

Agent-capability governance is **early**. There is no mature measurement vocabulary — no CVE feed, no canonical capability taxonomy, no industry gold set. So HURCULES publishes its own measured ceiling rather than hiding it: exact recall against human gold labels is currently **0.0**, semantic recall around **0.10**. Extraction is real and end-to-end, but its granularity differs from how humans name capabilities.

A trust layer's credibility *is* the product. A vendor that hides a 0.10 recall has already broken the promise it exists to make. So the honest number sits in the README next to the roadmap: raise measured recall on a public gold set, re-publish, repeat. Published, measured, and climbing beats claimed, unverifiable, and believed by no one.

## 6. Try it on your own repo

You don't have to take our word for the numbers — publishing them is the point.

```
pip install hurcules
```

Point it at any repository you're currently feeding to an agent fleet, and look at what comes out: capabilities, evidence, provenance, and an approval record your security team can sign. If the first run makes you uncomfortable about what your agents run on — that discomfort is a bill of materials finally arriving.

The agents are already acting. It's time to account for what they're built from.

---

*HURCULES — the trust layer for agent supply chains. Verified capability packages: provenance, proof, and approval for everything your agents consume. MIT open-core; self-analyzed on its own repository; hostile-by-default by design.*