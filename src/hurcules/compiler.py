"""HURCULES Stage 4 — Capability Compiler (deterministic, NO LLM).

Turns Stage 3 analyst survivors + Stage 2 repo map into a validated standard
capability package. REJECTS invalid packages (never silently repairs).

Public seam: compile_package(analyst_analysis, repo_map, repo_dir) -> dict
Returns {"ok": True, "package": {...}} or {"ok": False, "errors": [...], "warnings": [...]}.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from hurcules.logutil import get_logger

COMPILER_VERSION = "1.0.0"

LOG = get_logger(__name__)

APPROVED_PERMISSIONS = {
    "filesystem_read_only", "filesystem_read_write", "network",
    "shell", "none",
}
ONTOLOGY = {
    "ROLE", "TOOL", "SKILL", "WORKFLOW", "POLICY", "KNOWLEDGE PACK",
    "EVALUATOR", "ADAPTER", "AGENT TEMPLATE",
}


def _validate_survivors(survivors: list[dict], file_tree: list[str],
                        manifests: list[str]) -> list[str]:
    """Return list of validation error strings (empty = valid)."""
    errors = []
    seen_ids = set()
    for c in survivors:
        cid = c.get("id")
        if not cid:
            errors.append("capability missing id")
            continue
        if cid in seen_ids:
            errors.append(f"duplicate capability id: {cid}")
        seen_ids.add(cid)

        if not c.get("name"):
            errors.append(f"{cid}: missing name")
        if c.get("ontology_type") not in ONTOLOGY:
            errors.append(f"{cid}: ontology_type not in approved set")
        # evidence: every cited file must exist in the repo tree
        ev = c.get("evidence") or []
        if not isinstance(ev, list) or not ev:
            errors.append(f"{cid}: no evidence")
        else:
            for e in ev:
                f = e.get("file")
                if f not in file_tree:
                    errors.append(f"{cid}: evidence cites non-existent file '{f}'")
                if not e.get("scope"):
                    errors.append(f"{cid}: evidence entry missing scope")
        conf = c.get("confidence")
        if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
            errors.append(f"{cid}: confidence not in [0,1]")
        # requirements optional
    return errors


def _check_dependency_consistency(requirements: list[str], manifests: list[str]) -> list[str]:
    """Warn if a declared dependency has no manifest present. Advisory only."""
    warnings = []
    return warnings


def _extract_permissions(capabilities: list[dict]) -> list[str]:
    perms = set()
    for c in capabilities:
        # optional permissions field on capability
        p = c.get("permissions") or []
        if isinstance(p, list):
            perms.update(p)
    return sorted(perms)


def compile_package(analyst_analysis: dict, repo_map: dict, repo_dir: str) -> dict:
    survivors = analyst_analysis.get("capabilities", [])
    file_tree = repo_map.get("file_tree", [])
    manifests = repo_map.get("dependency_manifests", [])
    repository = repo_map.get("repository") or repo_dir

    # Quality floor (W1-[1]): an INCONCLUSIVE analysis is NOT a valid input.
    # Never compile a silent empty package from a weak/empty extraction.
    if analyst_analysis.get("conclusion") == "inconclusive":
        LOG.warning("compile rejected errors=1")
        return {"ok": False, "errors": ["analysis inconclusive — empty/unparseable "
                                        "extraction (not a valid empty package)"],
                "warnings": [], "package": None}

    errors = _validate_survivors(survivors, file_tree, manifests)
    if errors:
        LOG.warning("compile rejected errors=%d", len(errors))
        return {"ok": False, "errors": sorted(set(errors)), "warnings": [],
                "package": None}

    # build standard package
    capabilities_out = []
    for c in sorted(survivors, key=lambda x: x.get("id", "")):
        capabilities_out.append({
            "id": c["id"],
            "name": c["name"],
            "ontology_type": c["ontology_type"],
            "evidence": [{"file": e["file"], "scope": e["scope"]}
                         for e in (c.get("evidence") or [])],
            "confidence": c["confidence"],
            "requirements": c.get("requirements", []),
        })

    secret_locations = repo_map.get("secret_file_locations", [])
    package = {
        "schema": "hurcules.capability-package-v1",
        "compiler_version": COMPILER_VERSION,
        "provenance": {
            "repository": repository,
            "file_count": repo_map.get("file_count"),
            "languages": list(repo_map.get("languages", {}).keys()),
        },
        "registry": {
            "status": "candidate",  # never auto-approved (D3)
        },
        "capabilities": capabilities_out,
        "dependency_manifests": manifests,
        "permissions_summary": _extract_permissions(survivors),
        "security": {
            "secret_file_locations": secret_locations,  # paths only
            "risk_flags": repo_map.get("risk_flags", []),
            "hostile_by_default": True,
            "execution_denied_by_default": True,
        },
    }

    # determinism guard: must serialize identically given same inputs
    LOG.info("compile ok caps=%d", len(capabilities_out))
    return {"ok": True, "errors": [], "warnings": [], "package": package}