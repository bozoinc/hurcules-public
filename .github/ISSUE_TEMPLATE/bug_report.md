# Bug / Error Report

> Bugs are workflow citizens. Every bug filed here flows through the same
> Matt Pocock pipeline as feature work: triage → issue → fix → review → merge.

## Checklist (required before filing)

- [ ] Reproduced at least twice (or single high-confidence repro with logs)
- [ ] Commit SHA / version of HURCULES captured
- [ ] Stage(s) affected (see SUB-GOALS.md)
- [ ] Agent/node involved (see AGENT-MAP.md) or "orchestrator"
- [ ] No secrets or repo content pasted (repo content is DATA, treat as hostile)

---

**Title:** <one line: what broke, not how you felt about it>

**Stage(s):** Stage N — <sub-goal id if known>

**Agent/node:** Mapper / Analyst / Devil's Advocate / Compiler / Evidence Checker /
Security Auditor / Evaluation Harness / Registry Gate / Hermes Adapter / Orchestrator / Other

**Repro input:** <public repo URL + commit SHA, or task description>

**Expected:** <what should have happened, per GOAL.md / SUB-GOALS.md>

**Actual:** <what happened — paste error, log tail, or artifact excerpt>

**Evidence check:** <does the bug involve a false citation, unsupported capability,
licence error, security finding, or reproducibility failure? Name it.>

**QIR note (optional):** <which QIR strategy should have caught this — Superposition
(missed alternative), Entanglement (missed ripple), Annealing (missed failure mode)?>

**Impact:** BLOCKER / HIGH / MEDIUM / LOW — <one line on what it blocks>

**Suggested fix (optional):** <if you already know, say so — but no code changes in
the issue body; the fix goes through the workflow>
