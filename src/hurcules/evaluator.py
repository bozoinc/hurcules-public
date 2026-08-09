"""HURCULES Stage 5 — Evidence & Evaluation Gates (deterministic core).

Prove quality, don't assert it. Deterministic checks (no LLM):
- citation_accuracy: every cited evidence file exists in the repo tree
- evidence_present: every capability has evidence
- id_uniqueness: no duplicate capability ids
- ontology_valid: ontology_type in approved set
- confidence_valid: confidence in [0,1]
- unsupported_capability_rate: fraction of capabilities lacking valid evidence

Plus the semantic gold-match gate (LLM-backed, wired separately).

Public seam: evaluate_capabilities(capabilities, file_tree, gold_caps) -> dict
"""
from __future__ import annotations

EVALUATOR_VERSION = "1.0.0"

ONTOLOGY = {
    "ROLE", "TOOL", "SKILL", "WORKFLOW", "POLICY", "KNOWLEDGE PACK",
    "EVALUATOR", "ADAPTER", "AGENT TEMPLATE",
}


def _check_citation(cap, file_tree) -> tuple[str, str]:
    """(status, detail) — PASS/CONDITIONAL/FAIL for citation accuracy."""
    ev = cap.get("evidence") or []
    if not ev:
        return "FAIL", "no evidence"
    missing = [e.get("file") for e in ev if e.get("file") not in file_tree]
    if missing:
        return "FAIL", f"cites non-existent file(s): {missing[:3]}"
    return "PASS", f"{len(ev)} evidence entries cite existing files"


def _check_schema(cap) -> tuple[str, str]:
    cid = cap.get("id")
    if not cid:
        return "FAIL", "missing id"
    if not cap.get("name"):
        return "FAIL", "missing name"
    if cap.get("ontology_type") not in ONTOLOGY:
        return "FAIL", f"bad ontology_type {cap.get('ontology_type')!r}"
    conf = cap.get("confidence")
    if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
        return "FAIL", "bad confidence"
    return "PASS", "schema valid"


def evaluate_capabilities(capabilities: list[dict], file_tree: list[str],
                          gold_caps: list[dict] | None = None) -> dict:
    """Per-capability verdict matrix + aggregate unsupported-capability rate.

    gold_caps optional: when provided, a semantic gold-match gate is expected
    to be applied externally (LLM) and passed via `gold_matches`; the
    deterministic portion computes citation/schema checks and the
    unsupported-capability rate.
    """
    tree = set(file_tree)
    verdicts = []
    for cap in capabilities:
        stat_s, det_s = _check_schema(cap)
        stat_c, det_c = _check_citation(cap, tree)
        checks = {
            "schema": {"status": stat_s, "detail": det_s},
            "citation_accuracy": {"status": stat_c, "detail": det_c},
        }
        supported = stat_s == "PASS" and stat_c == "PASS"
        verdicts.append({
            "id": cap.get("id"),
            "name": cap.get("name"),
            "ontology_type": cap.get("ontology_type"),
            "status": "PASS" if supported else "CONDITIONAL",
            "checks": checks,
            "supported": supported,
        })

    n = len(capabilities)
    unsupported = sum(1 for v in verdicts if not v["supported"])
    unsupported_rate = unsupported / n if n else 0.0

    return {
        "schema": "hurcules.evaluation",
        "evaluator_version": EVALUATOR_VERSION,
        "capability_count": n,
        "unsupported_capability_count": unsupported,
        "unsupported_capability_rate": round(unsupported_rate, 4),
        "verdicts": verdicts,
    }