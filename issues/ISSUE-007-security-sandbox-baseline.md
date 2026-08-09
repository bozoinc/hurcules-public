# Security & Sandbox Baseline (moved up per D3)

## Security & Sandbox Baseline — Stage 1-2 dependency

**Ladders to:** GOAL.md (hostile-by-default; spawn-from-day-one sandboxed, D3).

## What
Because spawns happen from day one (D3), the sandbox boundary is a Stage 1-2
dependency, NOT Stage 7. Baseline: isolated workspace for analysis + isolated
runtime for any spawned agent. Repo content is DATA; execution denied by default.

## Acceptance Criteria
- [ ] Analysis workspace: read-only, isolated, disposable
- [ ] Spawn sandbox: no host FS, no SSH keys, no GitHub tokens, no cloud creds,
      no personal files, no Docker socket, no privileged exec, restricted/disabled
      network, CPU/RAM/storage limits, timeout, full logs, disposable FS
- [ ] Sandbox is a real system boundary, not a system-prompt promise
- [ ] No analysed repo code ever touches host credentials
- [ ] Red-team pass (Annealing): path traversal, env leak, socket access, fork
      bombs — every escape is a blocker
- [ ] SECURITY.md posture enforced in CI (analysis yes, execution no)

## Dependencies
- ISSUE-001 (contract)

## Notes
Sandbox depth decision (container vs worktree vs permissive-local) resolved here
— implementation choice, default to container if available.