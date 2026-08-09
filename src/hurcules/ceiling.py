"""HURCULES gold-set extraction CEILING scorer (deterministic, no LLM, no network).

The ceiling test measures how well an extraction pipeline (analyst -> advocate ->
compiler) reconstructs the HUMAN-VERIFIED gold capabilities of a repository.
This module is the honest scoring core: pure name-matching + evidence checks,
so the numbers can be trusted and re-run without touching a model.

Public seam: ceiling_score(extracted_caps, gold_caps) -> dict
"""
from __future__ import annotations

from hurcules.logutil import get_logger

CEILING_VERSION = "1.0.0"

LOG = get_logger(__name__)


def normalize_name(name) -> str:
    """Lowercase + strip — same normalization as the analyst quality matcher."""
    return str(name).strip().lower()


def tokens(name) -> set[str]:
    """Whitespace-token bag for semantic (Jaccard) matching.

    Handles the observed gap: gold names are human-authored ("YAML workflow
    engine (DAG)") while extracted names are model-authored ("workflow
    executor engine") — identical meaning, zero exact-string overlap. Token
    Jaccard is deterministic, dependency-free, and catches that overlap.
    """
    import re
    return {t for t in re.split(r"[^a-z0-9]+", normalize_name(name)) if t}


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def has_valid_evidence(cap: dict) -> bool:
    """Valid evidence = a non-empty evidence list (anti-hallucination floor)."""
    ev = cap.get("evidence")
    return isinstance(ev, list) and bool(ev)


def _cap_id(cap: dict) -> str:
    return str(cap.get("id") or cap.get("name") or "")


def ceiling_score(extracted_caps: list[dict], gold_caps: list[dict]) -> dict:
    """Score extracted capabilities against the gold standard.

    Matching is by normalized capability NAME (lowercase+strip), assigned
    greedily one-to-one (each extracted cap claims at most one gold cap, and
    vice-versa) so duplicate names cannot inflate the score.

    Returns a dict with:
      precision         = matched / extracted            (are we hallucinating?)
      recall            = matched / gold                 (did we find it all?)
      unsupported_rate  = without_valid_evidence / extracted
      matching_ids      = extracted ids matched to gold
      missing_gold      = gold ids not surfaced
      extra             = extracted ids with no gold counterpart
      unsupported_ids   = extracted ids with empty evidence
    """
    # bucket gold capabilities by normalized name
    gold_by_name: dict[str, list[int]] = {}
    for i, g in enumerate(gold_caps):
        n = normalize_name(g.get("name"))
        if n:
            gold_by_name.setdefault(n, []).append(i)

    used_gold: set[int] = set()
    matched_idx: set[int] = set()
    for idx, cap in enumerate(extracted_caps):
        n = normalize_name(cap.get("name"))
        if not n:
            continue
        for gi in gold_by_name.get(n, []):
            if gi not in used_gold:
                used_gold.add(gi)
                matched_idx.add(idx)
                break

    matching_ids = sorted(_cap_id(c) for i, c in enumerate(extracted_caps)
                          if i in matched_idx)
    missing_gold = sorted(_cap_id(g) for i, g in enumerate(gold_caps)
                          if i not in used_gold)
    extra = sorted(_cap_id(c) for i, c in enumerate(extracted_caps)
                   if i not in matched_idx)
    unsupported = sorted(_cap_id(c) for c in extracted_caps
                         if not has_valid_evidence(c))

    n_ext = len(extracted_caps)
    n_gold = len(gold_caps)
    n_match = len(matching_ids)

    LOG.info("ceiling scored extracted=%d gold=%d match=%d", n_ext, n_gold, n_match)

    return {
        "schema": "hurcules.ceiling-score",
        "ceiling_version": CEILING_VERSION,
        "extracted_count": n_ext,
        "gold_count": n_gold,
        "matching_count": n_match,
        "precision": round(n_match / n_ext, 4) if n_ext else 0.0,
        "recall": round(n_match / n_gold, 4) if n_gold else 0.0,
        "unsupported_count": len(unsupported),
        "unsupported_rate": round(len(unsupported) / n_ext, 4) if n_ext else 0.0,
        "matching_ids": matching_ids,
        "missing_gold": missing_gold,
        "extra": extra,
        "unsupported_ids": unsupported,
    }


def ceiling_score_semantic(extracted_caps: list[dict], gold_caps: list[dict],
                           threshold: float = 0.35) -> dict:
    """Ceiling with token-Jaccard semantic matching (deterministic, no LLM).

    Exact-name matching alone undercounts real capability extraction because
    gold names are human-authored while extracted names are model-authored
    ("YAML workflow engine (DAG)" vs "workflow executor engine"). This variant
    greedily matches an extracted cap to the gold cap with the HIGHEST Jaccard
    similarity when that similarity >= threshold. The threshold is a policy
    knob: raise to be stricter, lower to allow more fuzzy matches.

    Returns the same shape as ceiling_score with a `matcher` field.
    """
    gold_by_name_orig: list[dict] = list(gold_caps)

    def best_gold(ext: dict) -> tuple[float, int]:
        # highest (score, gold_index) over unused gold caps with score >= threshold
        best_score, best_idx = 0.0, -1
        ext_name = str(ext.get("name", ""))
        for gi, g in enumerate(gold_by_name_orig):
            if gi in used_gold_idx:
                continue
            s = jaccard(ext_name, str(g.get("name", "")))
            if s > best_score:
                best_score, best_idx = s, gi
        return (best_score, best_idx)

    used_gold_idx: set[int] = set()
    matched_set: set[int] = set()
    for idx, cap in enumerate(extracted_caps):
        score, gi = best_gold(cap)
        if gi != -1 and score >= threshold:
            used_gold_idx.add(gi)
            matched_set.add(idx)

    matching_ids = sorted(_cap_id(c) for i, c in enumerate(extracted_caps)
                          if i in matched_set)
    missing_gold = sorted(_cap_id(g) for i, g in enumerate(gold_by_name_orig)
                          if i not in used_gold_idx)
    extra = sorted(_cap_id(c) for i, c in enumerate(extracted_caps)
                   if i not in matched_set)
    unsupported = sorted(_cap_id(c) for c in extracted_caps
                         if not has_valid_evidence(c))

    n_ext = len(extracted_caps)
    n_gold = len(gold_by_name_orig)
    n_match = len(matching_ids)

    return {
        "schema": "hurcules.ceiling-score",
        "ceiling_version": CEILING_VERSION,
        "matcher": f"token-jaccard>={threshold}",
        "extracted_count": n_ext,
        "gold_count": n_gold,
        "matching_count": n_match,
        "precision": round(n_match / n_ext, 4) if n_ext else 0.0,
        "recall": round(n_match / n_gold, 4) if n_gold else 0.0,
        "unsupported_count": len(unsupported),
        "unsupported_rate": round(len(unsupported) / n_ext, 4) if n_ext else 0.0,
        "matching_ids": matching_ids,
        "missing_gold": missing_gold,
        "extra": extra,
        "unsupported_ids": unsupported,
    }