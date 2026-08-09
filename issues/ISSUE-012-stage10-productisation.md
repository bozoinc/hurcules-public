# Stage 10 — Productisation (foundation + product-infra backlog)

Parent: ISSUE-009-wayfinder-fog-map.md

## Foundation (DONE 2026-08-06)
- src/hurcules/moat.py — moat-asset inventory (10.7)
- src/hurcules/product.py — marketplace() (10.5/10.6), Org shell (10.1),
  readiness_report() (gate)
- tests/test_product.py — 11 tests

## Product-infra backlog (real work, NOT done — do not stub as complete)
- 10.1 real auth + user accounts + sessions
- 10.2 private-repo ingestion (no grant leaks, sandboxed analysis)
- 10.3 organisation policies
- 10.4 hosted analysis + dashboards
- 10.6 billing + marketplace payments

## Gate
the product owner decides product readiness. No vanity metrics (capability count != success).
