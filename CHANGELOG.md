# Changelog

All notable changes to HURCULES are documented here. Follows Keep a Changelog
format and SemVer (see docs/adr/ADR-0001).

## [v0.7.0] — 2026-08-09
Wave 4 — Usable & sellable. 335/335 pytest, coverage 93.08%.

### Added
- `src/hurcules/marcus.py` — the D6 centrepiece: a novice UX step-machine
  (submit → ingest → review → approve → done) with hostile-by-default URL
  validation and injectable ingest (offline stub for demos). `run_novice`
  is an automated non-coder persona that proves the whole flow end-to-end
  with zero human input. Fake credentials in URLs are rejected.
- `src/hurcules/discovery_queue.py` — sweep cost control: state-based dedupe
  (skip done/failed), allow/deny lists, budget truncation, per-repo timeout
  seam.
- `src/hurcules/dash.py` — localhost-first read-only dashboards (catalog /
  spend / approvals / sandbox), stdlib http.server, HTML-escaped render,
  127.0.0.1-only bind, never crashes on missing data files.
- `docs/wave4/design-private-repo-and-auth.md` — design for [15] private-repo
  ingestion (air-gapped sanitized copy; user creds NEVER touch HURCULES) and
  [17] auth/org/billing (authentik OIDC + FOSS-gated billing adapter).
  Honest design deliverables; ISSUE-012 blockers remain blockers.

## [v0.6.0] — 2026-08-09
Wave 3 — Trust the loop. 286/286 pytest, coverage 93.21%.

### Added
- `src/hurcules/feedback.py` — feedback recorder (the missing half of the D5
  spawn loop): `record_feedback` (JSON store, deterministic), history,
  `summarize` (pass_rate/usages/flags/edge_cases, no div-by-zero),
  `attach_to_package` (deep copy + feedback key, original unmutated).
- `src/hurcules/lifecycle.py` — registry lifecycle state machine on the
  existing Registry (zero edits to it): candidate/approved + deprecated/
  revoked/superseded, `transition` writes an audit_trail, nothing leaves
  revoked/superseded, nothing goes backwards, `is_stale`/`mark_stale` on
  upstream commit change.
- `src/hurcules/approval.py` — auditable 4-part D4 approval: build_artifact
  (eval+summary+provenance+live_demo), canonical digest, sign/verify
  (audit HMAC, documented not PKI), `record_approval`,
  `require_approval_before_spawn` gate (approved + artifact + signature).

### Changed
- Stopped tracking `.coverage` (generated artifact, gitignored).

## [v0.5.0] — 2026-08-09
Wave 2 — Trust the boundary. 239/239 pytest, coverage 92.84%.

### Added
- `src/hurcules/injection.py` — deterministic prompt-injection battery:
  10-case adversarial corpus (README overrides, hidden comments, crafted
  JSON, env.example, changelog, system-role JSON, XML reminder, base64
  obfuscation). `run_battery(analyst_fn)` — marker echo, empty output, or
  crash all count as exploit/fail. Converts SUB-GOAL 3.7 into a test suite.
- `src/hurcules/license_gate.py` — `detect_license` (permissive/copyleft/
  proprietary/unknown/none) + `check_license(repo_dir, marketplace)`.
  Proprietary/unknown always blocked; no-license blocked only when
  marketplace distribution is requested.
- `src/hurcules/secrets_hygiene.py` — deterministic secret-value scan
  (never returns VALUES, only pattern names + paths), the pilot's hexyl
  `${{ secrets.X }}` CICD regression fixture, and `verify_no_values_in_package`
  hard gate before registry.
- `src/hurcules/profiles.py` — capability-scoped sandbox profiles
  (none/readonly/readwrite/network/shell), `profile_for` most-permissive-
  wins. `SandboxLimits.network` + docker_args emit `--network none|bridge`;
  `Sandbox.run()` no longer hardcodes no-network.

### Findings (honest)
- The injection battery caught a real bug on landing: a syntax error in the
  system-role-json corpus payload (escaped-quote continuation). Fixed in
  review; battery proves both directions (well-behaved analyst passes all,
  naive analyst flagged exploitable).

## [v0.4.0] — 2026-08-09
Phase A — Enterprise hardening. 186/186 pytest, coverage 92.3%, pip-installable.

### Added
- `pyproject.toml` (PEP 621, src layout) + `hurcules` console entry point:
  `hurcules --version / ingest / ceiling`. Verified `pip install -e .`.
- `src/hurcules/logutil.py` — single stdlib logging config (`HURCULES_LOG_LEVEL`,
  default WARNING), idempotent; surgical log statements across
  mapper/analyst/compiler/evidence/ceiling/cross_validate.
- `routes.py` hardening — `classify_http_error` (transient/non-transient/
  unknown pure fn), per-route exponential retry/backoff on 429/5xx/timeout
  (injectable for tests), `RouteDown`/`NoHealthyRoute` taxonomy.
- CI coverage gate `>=80%` (actual 92.3%) + stale local-route env fixed.

### Model-agnostic note (packaging makes it explicit)
HURCULES is model-agnostic: deterministic stages never call an LLM; the
analyst/advocate plug into ANY OpenAI-compatible endpoint via routes
(base_url + model + key). Free OmniRoute models are the default, not a lock.

## [v0.3.0] — 2026-08-09
Wave 1 — Trust the model. Exit gate: 167/167 pytest green, INCONCLUSIVE
quality floor live, evidence + cross-model + ceiling harnesses built.

### Added
- `src/hurcules/routes.py` — LLM route policy: health probe, per-stage
  selection, failover client, ExtractionFloor (empty/unparseable output is
  INCONCLUSIVE, never a silent valid empty package). Local llama-server
  removed from defaults; OmniRoute free routes only.
- `src/hurcules/evidence.py` — deterministic evidence-validity checker:
  every claimed file exists AND scope text appears in the file content.
- `src/hurcules/cross_validate.py` — cross-model validation: run analyst
  with ≥2 models on the same mapper output, require agreement before
  registry admission.
- `src/hurcules/ceiling.py` + `scripts/run_gold_ceiling.py` — gold-set
  extraction ceiling (precision/recall/unsupported) with exact-name AND
  token-Jaccard semantic matching.

### Changed
- `analyst.analyze()` reports `conclusion: ok|inconclusive`; blank/unparseable
  model replies short-circuit to INCONCLUSIVE instead of crashing.
- `compiler.compile_package()` rejects inconclusive input.
- `scripts/discovery_to_pipeline.py` uses Router (probe + failover), no local
  route.

### Findings (honest, from the gold-set ceiling)
- Exact-name ceiling: recall 0.0; semantic (Jaccard) recall ~0.10 —
  extractions are evidence-backed (unsupported_rate 0.0) but operate at a
  different granularity than human gold labels.
- OmniRoute free-tier today: 1 model verified working (nemotron-3-super 120b);
  others return 400/403 — cross-model therefore honestly refuses until ≥2
  healthy routes exist. Single-model pipeline unaffected (failover).

## [v0.2.0] — 2026-08-09
Wave 0 — Trust the baseline. Exit gate: 104/104 pytest green,
determinism golden diff IDENTICAL, cost ledger live.

### Added
- ADR process + ADR-0001 (versioning/changelog cadence) — `docs/adr/`.
- CI pipeline (GitHub Actions: ruff fatal lint + full pytest + mapper
  determinism golden-diff + Docker sandbox job) — `.github/workflows/ci.yml`.
- Cost & duration ledger — `src/hurcules/ledger.py`: per-stage model, route,
  messages, latency, duration; persisted to `data/run-reports/` per run.
- Deterministic-runs harness — `scripts/check_determinism.py`
  (stored-golden byte-diff; cross-invocation stable).

### Changed
- `scripts/discovery_to_pipeline.py`: LLM route env-driven
  (`HURCULES_BASE`/`HURCULES_MODEL`), `get_key()` tolerant of missing
  mem0.json, ledger-instrumented (writes run-report per ingest).

### Fixed (found by the new determinism gate)
- Mapper digest now normalizes the absolute clone path in
  `repository` before hashing — output was byte-unstable across runs.

## [v0.1.0] — 2026-08-09
Baseline tag. Stages 0–10 foundation complete:
- Repo → mapper → analyst + devil's advocate → compiler → eval gates →
  registry → human approval (D4) → composition → sandboxed execution →
  productisation foundation (moat + marketplace).
- 95/95 pytest green on baseline tree.
- Pilot artifact: discovery_to_pipeline.py env-routing change +
  sharkdp__hexyl entry committed.