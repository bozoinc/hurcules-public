# Stage 8 — Discovery (autonomous candidate search)

Parent: ISSUE-009-wayfinder-fog-map.md (deferred stages)
Ladders to: GOAL.md — one-repo ingestion is trustworthy, now find more repos.

## What
Discover public GitHub repos that could yield NEW validated capabilities,
rank them, and feed each through the SAME ingestion pipeline as the gold set
(no shortcuts). Discovery is gated by cost/rate controls.

## Acceptance Criteria (SUB-GOALS Stage 8)
- [ ] 8.1 GitHub search (public repos) with minimal-permission token (gh CLI, bozoinc)
- [ ] 8.2 Ranking/scoring candidates by relevance signals (stars, activity, license, language)
- [ ] 8.3 Each discovered repo goes through the SAME ingestion pipeline (map->analyst->advocate->compiler) — no shortcuts
- [ ] 8.4 Rate-limit + cost controls on discovery (max candidates/run, clone cap, pinned commits)

Exit gate: discovery feeds the pipeline; no regressions in Stages 2-5 (61/61 still green).

## Dependencies
- ISSUE- (stage2 mapper) for ingestion
- gh CLI authenticated (bozoinc) for search

## Notes
- Ranking must be a pure, deterministic function (testable without network).
- Network fetch shells to `gh api` / `git clone`; mock in tests.
- Do NOT clone/analyse private repos (out of scope v1).