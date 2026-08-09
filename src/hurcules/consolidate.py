"""HURCULES Stage 3 — capability consolidation (precision tuning).

Root cause of low precision: the analyst over-produces granular candidates
(e.g. "JSON parsing", "JSON generation", "JSON query interpreter" for one gold
capability "JSON parsing and value model"). This pass deterministically merges
near-duplicate candidates by name-overlap into consolidated capabilities.

Deterministic, NO LLM, no embeddings. Public seam:
consolidate(candidates) -> list[dict]
"""
from __future__ import annotations

import re

CONSOLIDATE_VERSION = "1.0.0"

STOP = {"a", "an", "the", "and", "or", "of", "for", "to", "in", "with", "on",
        "using", "at", "is", "tool", "system", "support", "capability"}

_MERGE_WORDS = {
    "parsing", "parser", "parse", "generation", "generator", "generate",
    "interpreter", "interpret", "query", "validation", "validat", "engine",
    "runtime", "framework", "management", "handler", "handling", "support",
    "integration", "adapter", "interface", "library", "module", "utility",
    "processing", "process", "render", "rendering", "format", "formatter",
}


def norm_tokens(name: str) -> set[str]:
    parts = re.split(r"[^a-z0-9]+", str(name).lower())
    return {p for p in parts if p and p not in STOP}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _mergeable(a: dict, b: dict, threshold: float = 0.45) -> bool:
    """Two candidates merge if: name-overlap is high, OR (same ontology type
    and they share a meaningful topic token beyond stop/generic words)."""
    ta, tb = norm_tokens(a.get("name", "")), norm_tokens(b.get("name", ""))
    if jaccard(ta, tb) >= threshold:
        return True
    if a.get("ontology_type") == b.get("ontology_type"):
        common = ta & tb
        if any(t not in _MERGE_WORDS for t in common):
            return True
    return False


def consolidate(candidates: list[dict], threshold: float = 0.55) -> list[dict]:
    """Merge near-duplicate candidates into consolidated capabilities.

    Uses greedy clustering (deterministic order): each candidate joins the
    first cluster it's mergeable with; else starts a new cluster. Cluster name
    = longest member name; evidence unioned; confidence = max; requirements
    unioned.
    """
    clusters: list[dict] = []
    for c in sorted(candidates, key=lambda x: x.get("id", "")):
        placed = False
        for cl in clusters:
            if _mergeable(cl, c, threshold):
                cl["evidence"] = cl.get("evidence", []) + c.get("evidence", [])
                # dedupe evidence by (file, scope)
                seen = set()
                ev = []
                for e in cl["evidence"]:
                    k = (e.get("file"), e.get("scope"))
                    if k not in seen:
                        seen.add(k)
                        ev.append(e)
                cl["evidence"] = ev
                cl["confidence"] = max(cl.get("confidence", 0), c.get("confidence", 0))
                reqs = set(cl.get("requirements", [])) | set(c.get("requirements", []))
                cl["requirements"] = sorted(reqs)
                cl["name"] = max(cl["name"], c.get("name", ""), key=len)
                cl["members"] = sorted(set(cl.get("members", [cl["id"]]) + [c.get("id", "")]))
                placed = True
                break
        if not placed:
            clusters.append({
                "id": c.get("id", ""),
                "name": c.get("name", ""),
                "ontology_type": c.get("ontology_type", ""),
                "evidence": c.get("evidence", []),
                "confidence": c.get("confidence", 0.0),
                "requirements": sorted(c.get("requirements", []) or []),
                "members": [c.get("id", "")],
            })
    return clusters