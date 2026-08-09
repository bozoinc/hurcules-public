# HURCULES — Context (grill session record)

## Decisions locked in the grill (2026-08-05)

### D1 — First users (Stage 0 contract)
- **Decision:** the Product Owner + Hermes are the first users (dogfood). External developers/
  advanced agent builders are the monetization target IF the product proves out.
- **Rationale:** We're the ones building it; dogfooding validates quality gates
  against real pain; spec itself says "Hermes can be your first internal user."
- **Ripple (entanglement):** Registry format + approval gates designed for
  internal single-tenant use first; multi-tenant (accounts, orgs, billing)
  deferred to Stage 10. External usability is a design input, not a Stage 1 gate.

### D2 — First gold-standard case + success bar (Stage 1 contract)
- **Decision:** First repo to feed HURCULES = **Archon** (coleam00/Archon,
  already cloned at ~/projects/Archon).
- **Usage loop (what "works" means):** point HURCULES at Archon → it produces an
  agent template capturing Archon's abilities → Hermes then uses that template to
  (a) build a new agentic harness with Archon's abilities, (b) create a new agent,
  or (c) review/write high-performance code using Archon's workflow abilities.
- **Success bar (parity test):** FAIL = HURCULES cannot produce results at the
  same caliber as Archon's own abilities. The generated template must let Hermes
  perform at Archon's level, not merely summarize Archon.
- **Ripple (entanglement):** "Usability" barrier in GOAL.md now has teeth —
  parity, not just "without reverse-engineering." Stage 6 Hermes adapter is the
  parity test surface. Archon's own pipeline (workflow engine, YAML nodes, git
  worktrees, review patterns) becomes the capability-ontology vocabulary test case.

### D3 — Spawn policy (contract override)
- **Decision:** Option C — spawn-from-day-one, sandboxed. "Do not spawn agents"
  is REINTERPRETED as "no spawn WITHOUT explicit human approval" — not "no spawn
  at all." The product owner does not recall authoring the absolute no-spawn rule; it came from
  the spec's generic senior-engineer advice. The product owner overrides it for HURCULES.
- **Why C fits:** the sandbox boundary exists precisely so approved capabilities
  can run; proving parity with Archon (D2) requires Hermes to actually build a
  harness from Archon's extracted abilities. Prohibition would make the success
  bar untestable.
- **Ripple (entanglement):** Sandbox becomes a Stage 1-2 DEPENDENCY, not Stage 7
  — any spawn needs isolation from day one. "Approved" is still a human word
  (the product owner signs off). The spec's other restrictions (no execution of untrusted repo
  code on host, no secrets, no auto-approval) remain intact — they bind the
  ANALYSED repo, not Hermes's spawned agents.

### D4 — Approval ritual for a spawn (Stage 0 contract)
- **Decision:** "Approved" = the product owner sees ALL FOUR, in combination, before any spawn:
  1. Evaluation results (passed the test suite)
  2. Capability package summary (what it claims Archon/Hermes can do)
  3. Provenance (which files/lines/commits the abilities came from)
  4. A live demo (watch the spawned agent do one real task first)
- **No exceptions:** no spawn without this four-part approval, every time.

### D5 — Spawn workflow is TEST-CENTRIC (architecture shaping)
- **Decision:** Spawning is not a one-shot "approve → spawn → done" event.
  Testing the spawns is INTEGRAL to the project moving forward — spawns are part
  of a continuous evaluate-and-improve loop, not the end of the pipeline.
- **Reading (to confirm):** every spawn gets evaluated; evaluation results feed
  back into capability quality and the registry; the spawn → test → learn loop
  IS how HURCULES improves. A spawn without its test loop is unfinished work.
- **Ripple (entanglement):** Evaluation Harness (Stage 5) and Hermes Adapter
  (Stage 6) are joined in a feedback cycle, not sequential handoffs. The live
  demo in D4 is itself a test artifact. Registry stores spawn-test outcomes, not
  just package metadata. This strengthens the graph: spawn → evaluate → feed back.

### D6 — The real success bar: NON-TECHNICAL USABILITY (contract centerpiece)
- **Decision:** HURCULES PASSES when an average person with hardly any computer
  skills — let alone coding skills — can use/access the Archon agent template and
  produce a truly robust, efficient, capable harness just as good as a person with
  actual coding or engineering skills could.
- **Origin:** the Product Owner's initial idea was one-and-done packages; on reflection, a
  SELF-IMPROVING capability (D5) is the better end product / agent template.
- **What it means (parity redefined):** the test is not "matches Archon's output"
  — it's "a non-coder, using only the template, gets senior-engineer-quality
  results." The template must carry the engineering INSIDE it (workflows, checks,
  recovery, guidance) so the human drives intent, not mechanics.
- **Ripple (entanglement):**
  - Usability barrier in GOAL.md is upgraded: novice-operable, not just
    "without reverse-engineering."
  - Template schema must include operator-facing instructions (novice-safe),
    not just agent-facing internals.
  - Evaluation harness gains a "novice pilot" test case: a non-technical persona
    runs the template; PASS = quality output without hand-holding.
  - Connects to SLFN context: band members (~1500, Treaty 6) are exactly the
    non-technical users this serves; aligns with the "Tech baby" persona research.
  - The learning loop (D5) is what lets the template close the gap — each tested
    spawn makes the template easier and stronger for the next novice.

## Open questions (grill in progress)
- Q5: Sandbox depth for v1 spawns (full container isolation vs worktree-only vs
  permissive-local)? — implementation decision, carry to PRD/issues phase.

## Decisions added post-grill (2026-08-05)

### D7 — Persona correction
- **Decision:** The PRD user story persona is **Marcus**, a tech-curious
  entrepreneur with no coding background (not the SLFN band-member example used
  earlier). HURCULES' audience is anyone non-technical who wants senior-quality
  agent results — Marcus is the concrete stand-in.
- **Ripple:** All novice-usability test cases (D6) and the evaluation plan use
  the Marcus persona. SLFN context remains relevant but is not the primary
  persona framing.

### D8 — Gold-set risk posture (safe-only for now)
- **Decision:** Keep the 1 no-licence (nolicense) and 1 suspicious-scripts
  (suspicious) gold cases already created, but do NOT add more legal/security-
  sensitive cases for now. Stick to safe, permissive-license (MIT/Apache/BSD/
  CC0) repos going forward — the "90%ers" — until the project is further along.
- **Ripple:** Future gold additions are safe-only; the two sensitive cases stay
  quarantined/flagged but are not expanded. The claims-without-implementation
  case (claimgap) is safe to keep (MIT, no execution risk) and is retained.
