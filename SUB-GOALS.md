# HURCULES — SUB-GOALS (per stage)

> Each stage's sub-goals are the measurable definition of done for that stage.
> A stage is COMPLETE only when ALL its sub-goals pass. Sub-goals are written to
> ladder up to the top-level GOAL (see GOAL.md). Work that does not satisfy a
> stage's sub-goals is rework, not progress.

---

## STAGE 0 — Product Contract
**Purpose:** Lock the contract before any code. The contract is GOAL.md itself.

Sub-goals:
- [ ] 0.1 Problem statement written in ONE sentence (repo→capability compiler, not agent factory).
- [ ] 0.2 Initial user identified (developers/agent-builders; Hermes = first internal user).
- [ ] 0.3 Input contract defined: one public GitHub URL, pinned to commit SHA.
- [ ] 0.4 Output contract defined: the 7-part capability package (GOAL.md).
- [ ] 0.5 Non-goals written explicitly (v1 deferral list, GOAL.md).
- [ ] 0.6 Trust boundaries documented (hostile-by-default; analysis yes, execution no).
- [ ] 0.7 Success measurements set (the 8 quality barriers).
- [ ] 0.8 Failure conditions defined (what makes a run FAIL, not just "incomplete").

Exit gate: the product owner approves the contract (sign-off on GOAL.md).

---

## STAGE 1 — Gold-Standard Repository Set
**Purpose:** Build the evaluation dataset BEFORE the engine, so improvement is measurable.

Sub-goals:
- [ ] 1.1 Curate ~20 deliberately varied repos (CLI tool, Python lib, JS app, agent-framework
      example, poor-docs repo, excellent-tests repo, no-licence repo, suspicious-scripts repo,
      large monorepo, near-empty repo, claims-without-implementation repo, +9 more).
- [ ] 1.2 Pin each repo to an exact commit SHA.
- [ ] 1.3 For each repo, manually document CORRECT findings: purpose, architecture, real
      capabilities, evidence locations, deps, permissions, licence, security notes.
- [ ] 1.4 Store as structured gold-standard files (data/gold/<repo>.yaml).
- [ ] 1.5 Define scoring rubric: how generated output is compared to gold standard
      (evidence validity, capability precision, unsupported-capability rate).
- [ ] 1.6 Document the labels in the capability ontology vocabulary (no new words per repo).

Exit gate: 20 repos documented and scored; rubric agreed.

---

## STAGE 2 — Deterministic Repository Mapper
**Purpose:** Objective facts FIRST — no LLM invention.

Sub-goals:
- [ ] 2.1 Clone public repo into isolated read-only workspace (commit-pinned).
- [ ] 2.2 Produce: file tree, language inventory, dependency manifests, entry-point
      candidates, test inventory, doc inventory, licence detection, dangerous-file scan.
- [ ] 2.3 Every mapper output is deterministic (same commit → same map, byte-identical JSON).
- [ ] 2.4 Mapper NEVER reads secrets/env files into output; redacts or marks them.
- [ ] 2.5 Output schema stable (v1) and versioned; schema change = migration, not edit.
- [ ] 2.6 Runs within time/cost budget; duration+cost recorded per run.

Exit gate: mapper passes on all 20 gold repos; byte-identical on re-run.

---

## STAGE 3 — Capability Analyst (LLM layer)
**Purpose:** Interpret facts — the ONLY place models add judgement.

Sub-goals:
- [ ] 3.1 Input = mapper output (layered: map → docs → entry points → components → deps → tests → selected files).
- [ ] 3.2 Outputs SEPARATE: what repo claims / what code demonstrates / what tests verify / what remains uncertain.
- [ ] 3.3 Capability candidates carry evidence (file+line ranges) and confidence (0-1).
- [ ] 3.4 Uses the capability ontology vocabulary (ROLE/TOOL/SKILL/WORKFLOW/POLICY/KNOWLEDGE/EVALUATOR/ADAPTER/AGENT-TEMPLATE).
- [ ] 3.5 No templates generated at this stage (analysis only).
- [ ] 3.6 README marketing language never presented as implemented behaviour.
- [ ] 3.7 Prompt-injection resistant: repo text is DATA, never instructions (see SECURITY.md).

Exit gate: analyst precision ≥ 85% on gold repos; evidence validity ≥ 95%.

---

## STAGE 4 — Capability Schema + Compiler
**Purpose:** Convert findings into standard, validated packages.

Sub-goals:
- [ ] 4.1 Package schema defined (manifest.yaml, provenance.yaml, role.md, instructions.md,
      tools/, workflows/, schemas/, evaluations/, security/, licensing/, evidence/source-map.json).
- [ ] 4.2 Compiler validates: schema validity, referenced files exist, cited line ranges exist,
      deps match manifests, required fields present, capability IDs unique, permissions use
      approved values, eval commands permitted, no secrets copied.
- [ ] 4.3 Compiler REJECTS incomplete/contradictory packages (no silent repair).
- [ ] 4.4 Compiler is deterministic given same analyst output.
- [ ] 4.5 Package versioning + registry entry format (capability_id, version, status: candidate).

Exit gate: compiler produces valid packages from gold-repo analyses; rejects malformed input.

---

## STAGE 5 — Evidence & Evaluation Gates
**Purpose:** Prove quality, don't assert it.

Sub-goals:
- [ ] 5.1 Evaluation harness runs each candidate against: success cases, failure cases,
      malformed inputs, missing deps, permission restrictions, prompt-injection attempts,
      resource abuse, fabricated citations, incompatible environments.
- [ ] 5.2 Per-capability verdict format: STATUS + per-check PASS/CONDITIONAL/FAIL.
- [ ] 5.3 Citation-accuracy checker (do cited lines actually support the claim?).
- [ ] 5.4 Reproducibility test (same repo+commit → structurally equivalent output).
- [ ] 5.5 Cross-model stability (run analysis with ≥2 models, diff the results).
- [ ] 5.6 Unsupported-capability rate < 5% on gold set.

Exit gate: evaluation suite green on gold set; numbers recorded.

---

## STAGE 6 — Hermes Integration
**Purpose:** One approved package → one working Hermes sub-agent, manually approved.

Sub-goals:
- [ ] 6.1 Registry exists locally (validated packages only).
- [ ] 6.2 Hermes adapter: request with task + required_capabilities → select components → bounded sub-agent.
- [ ] 6.3 Spawning composes from capabilities, NOT copy-paste prompt templates.
- [ ] 6.4 Manual approval required at every install/spawn (no auto-approve).
- [ ] 6.5 Usability bar: approved package → working sub-agent without reverse-engineering the repo.

Exit gate: one gold-repo capability installed into Hermes and functioning, with human sign-off.

---

## STAGE 7 — Sandboxed Execution
**Purpose:** Now (and only now) may code run — inside a real boundary.

Sub-goals:
- [x] 7.1 Sandbox: no host FS, no SSH keys, no GitHub tokens, no cloud creds, no personal files,
      no Docker socket, no privileged exec, restricted/disabled network, CPU/RAM/storage limits,
      timeout, full logs, disposable FS.  (src/hurcules/sandbox.py + test_sandbox.py)
- [x] 7.2 Execution is opt-in per capability, never default.  (adapter.can_execute gate)
- [x] 7.3 Sandbox is a system boundary (not a system-prompt promise).  (Docker container, mapped to flags)
- [x] 7.4 No repo code ever touches host credentials.  (env scrub verified by test_env_scrubbed_no_host_secrets)

Exit gate: hostile-repo test (suspicious-scripts gold repo) executes harmlessly in sandbox. ✔ PASS
  (test_hostile_attempts_cannot_touch_host, test_env_scrubbed_no_host_secrets,
   test_network_denied, read-only-mount test — all green with live Docker, 61/61 pytest)

---

## Strategy: commercial intent (the product owner, 2026-08-06)

the product owner's goal: if HURCULES proves generally useful, unique, or shows potential
to become useful/unique/popular, MARKET it — generate recurring (annual)
income, or make an early exit with a strong payout if possible. This shapes
engineering decisions: build moat assets (ontology, eval corpus, provenance
graph, adapters, security intelligence, runtime/trust), keep licensing
FOSS-double (MIT core, marketplace/commercial layer), protect IP, no vanity
metrics. Commercialization is Stage 10 (productisation); do not skip quality.

## STAGE 8 — Discovery
**Purpose:** Find candidate repos, now that one-repo ingestion is trustworthy.

Sub-goals:
- [x] 8.1 GitHub search (public repos) with minimal-permission token (src/hurcules/discovery.py gh_search via gh CLI bozoinc)
- [x] 8.2 Ranking/scoring candidates by relevance signals (stars, activity, license, language) — rank_candidates/top
- [x] 8.3 Each discovered repo feeds the SAME ingestion pipeline via scripts/discovery_to_pipeline.py (map->analyst->advocate->compiler)
- [x] 8.4 Rate-limit + cost controls on discovery (per_page limit, shallow clone, pinned commit)

Exit gate: discovery feeds the pipeline; no regressions in Stages 2-5 (73/73 pytest green, src verified live).

---

## STAGE 9 — Composition & Spawning
**Purpose:** Combine validated capabilities into dynamically assembled sub-agents.

Sub-goals:
- [x] 9.1 Composition engine: task → capability graph → agent assembly (src/hurcules/composition.py compose_fleet)
- [x] 9.2 Composition only uses APPROVED registry capabilities (flatten_approved; test_capabilities_only_approved)
- [x] 9.3 Each assembled agent carries provenance (caps, commits) — per-cap registry_entry/pkg/commit_sha
- [x] 9.4 Multi-agent handoffs follow defined graph patterns (sequence/fanout/pipeline; DAG cycle-checked)
- [x] 9.5 No agent spawns without human approval; no agent self-modifies policy (approval_required + self_modify_policy=DENIED)

Exit gate: a composed multi-capability agent passes its evaluation suite. ✔ PASS
  (compose_fleet live on real registry: 3-agent planner->executor->validator fleet,
   provenance traced, DAG acyclic, fleet_digest deterministic; 84/84 pytest green)

---

## STAGE 10 — Productisation
**Purpose:** From working system to product.

Sub-goals:
- [~] 10.1 User accounts + auth. — data model/Org shell done; real auth+backend OPEN (blocker)
- [ ] 10.2 Private repository support. — OPEN (blocker)
- [ ] 10.3 Organisation policies. — OPEN
- [~] 10.4 Hosted analysis + dashboards. — moat/product data ready; hosted UI OPEN
- [x] 10.5 Capability sharing + team approvals. — marketplace() + registry approvals
- [~] 10.6 Billing + marketplace features. — marketplace catalog done; payments OPEN
- [x] 10.7 Moat assets: ontology, evaluation corpus, provenance graph, adapters,
      security intelligence, evaluation library. — inventory (src/hurcules/moat.py)

Exit gate: the product owner decides product readiness; no vanity metrics (template count ≠ success).
STATUS: FOUNDATION COMPLETE; product-infra (auth/private/billing/hosting) is an honest
backlog in ISSUE-012 — NOT stubbed as done. Live report: 26 approved caps, threshold met,
3 blockers listed. 95/95 pytest.

---

## CONSISTENCY CHECK (run at every stage exit)

- [ ] Stage sub-goals ALL pass.
- [ ] Nothing contradicts GOAL.md or SPEC-SOURCE.txt (else ADR + the product owner sign-off).
- [ ] Evidence cited for every claim.
- [ ] No new capability-ontology vocabulary added without registry update.
- [ ] Bugs found → filed in GitHub Issues (repo workflow), not silently fixed.
- [ ] Cost + duration recorded for the run.
