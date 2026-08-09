# Wave 4 — Design: Private-Repo Ingestion [15] + Auth/Org/Billing [17]

Date: 2026-08-09
Status: DESIGN — recorded per plan ("do the design before the payments stack";
  "[17] only after [16] has proven the product is usable"). No code written
  yet for these two items; the design is the deliverable.
Repo: ~/projects/hurcules (bozoinc/hurcules, PRIVATE)

---

## [15] PRIVATE-REPO INGESTION — design

### Problem
HURCULES today is public-repos-only (scripts/discovery_to_pipeline.py:
"no private repos"). Enterprises' highest-value repositories are private.
The blocker: cloning a private repo means holding the user's credentials —
an unacceptable trust surface for a hostile-by-default tool.

### Non-negotiable constraints (from the existing contract)
- Repo content is DATA, never instructions (SECURITY.md, SUB-GOAL 3.7).
- No host credentials ever enter the analysis (mapper/compiler never read
  env/secrets; secrets_hygiene.verify_no_values_in_package is a hard gate).
- Execution is denied by default; sandbox is the only execution boundary.
- HURCULES must never COPY secrets into output (secrets_hygiene invariant).

### Design decision: AIR-GAPPED SANITIZED COPY, creds stay with the user
The user's credentials NEVER touch HURCULES. Instead:

1. **User-side clone (out of band).** The user (or their CI) clones the
   private repo themselves — `git clone --depth 1 git@github.com:org/repo`
   or with their own token — into a local directory.
2. **User-side sanitize.** A deterministic `make_sanitized_copy(src_dir,
   dest_dir)` step (new module, mirrors secrets_hygiene rules) copies the
   tree, REMOVING: `.git/`, `.env*`, `id_*`, embedded private keys,
   files > size cap, and any file matching the secret-value scan. The copy
   is the ONLY thing HURCULES ever sees.
3. **Ingest the copy as a plain directory.** `hurcules ingest --dir
   /path/to/sanitized-copy` — the existing mapper/analyst/compiler pipeline
   is already directory-based (map_repository takes a repo_dir); only the
   clone step is skipped. Zero pipeline changes needed.
4. **Post-condition guard.** `secrets_hygiene.verify_no_values_in_package`
   runs as a hard gate (already exists) — belt and suspenders.

### Why this is right (QIR Annealing: attack the obvious alternatives)
- Alternative: HURCULES holds a PAT and clones directly. REJECTED — a
  credential-holding tool is the single biggest attack surface; the pilot
  philosophy is hostile-by-default.
- Alternative: `gh repo clone` with the user's ambient token. REJECTED —
  ambient creds leak into subprocess env; mapper scans env vars and would
  flag itself.
- Air-gap wins: HURCULES never touches a credential; the sanitized copy is
  provably free of values (verifiable gate); the pipeline is unchanged.

### Deliverables when this is built (not now)
- `src/hurcules/sanitize.py`: make_sanitized_copy + tests
- `scripts/ingest_dir.py`: directory-ingest entry (or a `hurcules ingest
  --dir` flag)
- CLI surface: `hurcules ingest --dir ...`
- Design gate: `verify_no_values_in_package` on the sanitized copy BEFORE
  analysis (pre-check) AND on the package (post-check).

---

## [17] AUTH / ORG / BILLING — design

### Problem
Stage 10's honest blockers: real auth+accounts+sessions (10.1), org
policies (10.3), billing/marketplace payments (10.6). The plan gates this
behind [16]: only after Marcus proves a non-coder can complete the flow.

### Existing foundations (verified)
- `src/hurcules/product.py`: Org shell (10.1 data model: org_id/name),
  marketplace() listing approved caps with provenance, readiness_report()
  (the go/no-go gate). 11 tests. Deliberately NO auth/billing stub.
- `data/registry/`: approved capabilities with provenance (the catalog).
- FOSS mandate: everything must be self-hosted, no paid lock-in.

### Design decisions
1. **Auth: self-hosted FOSS, OIDC-standard.** The user already has the
   right candidate: **authentik** (cloned at ~/projects/authentik for the
   SLFN Business OS SSO — GPL-style, self-host-only). One self-hosted
   authentik instance serves BOTH SLFN Business OS and HURCULES org
   accounts via OIDC. Alternative (documented, not chosen): Ory Kratos —
   lighter but reinvents SSO; authentik is already on the machine and is
   the user's standard.
2. **Org model: extend the existing Org shell, don't invent.** The shell
   has Org(org_id, name); the auth layer maps an authenticated user to an
   org membership (claims from the OIDC token). Policies = per-org
   allow/deny on marketplace adoption + spend limits (feeds the existing
   ledger).
3. **Billing: FOSS-gated, never lock-in.** A payments provider must have a
   genuine free tier sufficient for production, or be self-hostable. The
   honest FOSS posture: the marketplace catalog + license grants ARE the
   commercial surface; billing is a thin adapter (Stripe is the pragmatic
   default but requires the free-tier-viable check per the FOSS mandate;
   OpenCollective-style self-hosted is the alternative). This stays a
   DESIGN until [16] proves usability — per the plan, don't build payments
   for a product nobody can use yet.
4. **Readiness gate unchanged:** `product.readiness_report()` is the
   go/no-go. It currently lists auth/private/billing as blockers. This
   design does NOT mark them done — it records the path, honestly.

### Sequencing (when the user says go)
1. [16] Marcus proven (this wave's buildable item).
2. [15] built (sanitize + --dir) — highest-value unchosen product blocker.
3. [17a] auth: authentik OIDC login → org session → policies.
4. [17b] billing adapter — only after 1-3 exist.

---

## Honest status
- [15]: DESIGNED, not built (sanitize.py + ingest --dir pending user go).
- [17]: DESIGNED, not built (authentik path + FOSS billing adapter pending
  [16] and user go).
- Nothing fabricated as done. The existing blockers in ISSUE-012 remain
  blockers; this doc is the path, not the claim.