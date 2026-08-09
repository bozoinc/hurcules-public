"""HURCULES W1-[2] — Cross-model validation (>=2 models must agree).

Single-model analysis can hallucinate; the pilot's fix is to run the analyst
with >=2 DIFFERENT models on the SAME deterministic mapper output and only
treat a capability candidate as validated when the models agree on it.
Agreement is keyed on the NORMALIZED name (model ids like "c1" are per-model
artifacts and never comparable across models).

Public seam:
  cross_validate(repo_map, clients, models) -> dict  (runs analyze() per model)
  validate_before_registry(candidates, agreement, ...) -> {ok, allowed, blocked}
  clients_from_router(router) -> (clients, models)   # one client per healthy route

Deterministic: no randomness, sorted outputs, no network unless a client
callable makes one. Clients are injectable for tests (see test_analyst).
"""
from __future__ import annotations

import re
from typing import Callable, Iterable, Optional

from hurcules.analyst import analyze
from hurcules.logutil import get_logger
from hurcules.routes import LLM_STAGES, RoutingClient, Router  # Router: signature reference only

CROSS_VALIDATE_VERSION = "1.0.0"

LOG = get_logger(__name__)


def normalize_name(name) -> str:
    """Normalize a capability name for cross-model comparison.

    Lowercases and strips whitespace/punctuation so "JSON Parser!", "JSON
    Parser", and "json-parser" compare equal. Returns "" for empty/missing.
    """
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()


def _capability_names(candidates: list[dict]) -> set[str]:
    """Normalized-name set of a model run's candidates ('' for nameless)."""
    return {normalize_name(c.get("name")) for c in candidates}


def cross_validate(repo_map: dict,
                   clients: list[Callable[[list[dict]], str]],
                   models: list[str]) -> dict:
    """Run the analyst with >=2 different models and compare candidates.

    clients: one callable per model (same contract as analyst.analyze).
    models:  model ids, parallel to clients. Returns a report dict:

      runs          per-model analyze() results (capabilities, ids, conclusion)
      support       {normalized_name: number of models that proposed it}
      agreement     sorted normalized names proposed by ALL models
      disagreement  sorted normalized names NOT proposed by all models
      verdicts      per-model: "agrees" | "disagrees" | "inconclusive"
      verdict       "validated" if agreement is non-empty else "disputed"

    An inconclusive run (empty/unparseable output — ExtractionFloor
    conclusion != "ok") proposes nothing; conservatively it voids agreement,
    because validation requires every model to confirm a candidate.
    """
    if len(clients) != len(models):
        raise ValueError(
            f"clients ({len(clients)}) and models ({len(models)}) must be parallel")
    if len(models) < 2:
        raise ValueError("cross-model validation requires >=2 models")

    runs: list[dict] = []
    for model, client in zip(models, clients):
        out = analyze(repo_map, client)
        caps = out.get("capabilities", [])
        runs.append({
            "model": model,
            "conclusion": out.get("conclusion"),
            "capability_count": len(caps),
            "capability_ids": [c.get("id") for c in caps],
            "capabilities": caps,
        })

    support: dict[str, set[str]] = {}
    for run in runs:
        for c in run["capabilities"]:
            norm = normalize_name(c.get("name"))
            if norm:
                support.setdefault(norm, set()).add(run["model"])

    agreement = {n for n, proposers in support.items()
                 if len(proposers) == len(models)}
    disagreement = set(support) - agreement

    verdicts: dict[str, str] = {}
    for run in runs:
        if run["conclusion"] != "ok":
            verdicts[run["model"]] = "inconclusive"
            continue
        names = _capability_names(run["capabilities"])
        verdicts[run["model"]] = (
            "agrees" if names and names <= agreement else "disagrees")

    LOG.info("cross_validate models=%d verdict=%s",
             len(models), "validated" if agreement else "disputed")
    return {
        "schema": "hurcules.cross-validation",
        "cross_validate_version": CROSS_VALIDATE_VERSION,
        "models": list(models),
        "runs": runs,
        "support": {n: len(proposers) for n, proposers in sorted(support.items())},
        "agreement": sorted(agreement),
        "disagreement": sorted(disagreement),
        "verdicts": verdicts,
        "verdict": "validated" if agreement else "disputed",
    }


def validate_before_registry(candidates: list[dict],
                             agreement: Iterable[str],
                             min_models: int = 2,
                             min_agreement_ratio: float = 0.5,
                             support: Optional[dict] = None,
                             total_models: Optional[int] = None) -> dict:
    """Gate candidates on cross-model agreement before registry admission.

    A candidate proceeds only if its normalized name is in `agreement` AND
    (when `support`/`total_models` are supplied) it was proposed by
    >= min_models models with ratio >= min_agreement_ratio. `agreement`
    from cross_validate() already implies "proposed by every model", so the
    count gates are optional.

    Returns {"ok": bool, "allowed": [candidates], "blocked": [detail dicts]}.
    ok is True iff nothing was blocked.
    """
    norms = {normalize_name(a) for a in agreement}
    allowed: list[dict] = []
    blocked: list[dict] = []
    for c in candidates:
        norm = normalize_name(c.get("name"))
        if not norm:
            blocked.append({"candidate": c, "reason": "missing name"})
            continue
        if norm not in norms:
            blocked.append({"candidate": c,
                            "reason": "no cross-model agreement"})
            continue
        if support is not None and total_models is not None:
            count = support.get(norm, 0)
            if count < min_models:
                blocked.append({"candidate": c,
                                "reason": f"proposed by {count} models "
                                          f"< min_models={min_models}"})
                continue
            ratio = count / total_models
            if ratio < min_agreement_ratio:
                blocked.append({"candidate": c,
                                "reason": f"agreement ratio {ratio:.2f} "
                                          f"< {min_agreement_ratio}"})
                continue
        allowed.append(c)
    return {"ok": len(blocked) == 0, "allowed": allowed, "blocked": blocked}


def clients_from_router(router: Router, stage: str = "cross_model"):
    """Build (clients, models) for cross_validate from a Router.

    One RoutingClient pinned to each healthy route (no cross-route failover,
    so every model's output is attributable to that model). Requires >=2
    healthy routes. Performs NO network calls itself.
    """
    if stage not in LLM_STAGES:
        raise ValueError(
            f"stage {stage!r} is deterministic and must not request an LLM "
            "client (analyst/advocate/judge/cross_model only)")
    healthy = router.healthy_routes()
    if len(healthy) < 2:
        raise RuntimeError(
            f"cross-model validation needs >=2 healthy routes, got {len(healthy)}")
    clients: list[RoutingClient] = []
    models: list[str] = []
    for r in healthy:
        client = RoutingClient([r], probe_fn=router._probe_fn)
        client.route = r  # pin provenance
        clients.append(client)
        models.append(r.model)
    return clients, models