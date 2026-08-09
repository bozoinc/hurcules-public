"""HURCULES W1-[4] — Evidence Validity Checker (deterministic, NO LLM).

Stronger than the compiler's file-tree citation check: verifies not just that
every claimed evidence file exists in the repo, but that the claimed scope text
actually appears in the file content at the pinned repo path.

Design:
- verify_evidence(package_or_capabilities, repo_dir) -> dict
    {cap_id: {'status': 'PASS'|'FAIL', 'missing_files': [...],
              'scope_missing': [...], 'detail': str}}
- verify_package(package, repo_dir) -> dict {'ok': bool, 'results': {...}}

Semantics:
- Evidence file paths are relative to repo_dir.
- scope is a free-text search string: checked as a case-insensitive substring
  of the file content (no LLM, no fuzzy matching).
- File missing                        -> FAIL, recorded in missing_files.
- File present but scope not found    -> FAIL, recorded in scope_missing.
- Empty/missing scope                 -> FAIL, recorded in scope_missing.
- Every evidence entry must verify for the capability to PASS.

Deterministic: same inputs, same output. No timestamps, no randomness.
"""
from __future__ import annotations

from pathlib import Path

from hurcules.logutil import get_logger

EVIDENCE_VERSION = "1.0.0"

LOG = get_logger(__name__)


def _extract_capabilities(package_or_capabilities) -> list[dict]:
    """Accept either a full package dict ({'capabilities': [...]}) or a bare
    list of capability dicts."""
    if isinstance(package_or_capabilities, dict):
        caps = package_or_capabilities.get("capabilities")
        if isinstance(caps, list):
            return caps
        return [package_or_capabilities]  # bare single-capability dict
    return package_or_capabilities


def _check_evidence_entry(entry: dict, repo: Path) -> tuple[list[str], list[str]]:
    """Return (missing_files, scope_missing) for one evidence entry.

    file path absent/missing -> missing_files; scope absent or not found in
    the file content -> scope_missing."""
    missing_files: list[str] = []
    scope_missing: list[str] = []

    f = entry.get("file")
    if not f or not isinstance(f, str):
        missing_files.append(str(f))
        return missing_files, scope_missing

    path = repo / f
    if not path.exists() or not path.is_file():
        missing_files.append(f)
        return missing_files, scope_missing

    scope = entry.get("scope")
    if not scope or not isinstance(scope, str):
        scope_missing.append(f)
        return missing_files, scope_missing

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        # Unreadable file: treat as scope-not-found, don't fabricate a match.
        scope_missing.append(f)
        return missing_files, scope_missing

    if scope.lower() not in content.lower():
        scope_missing.append(f)

    return missing_files, scope_missing


def _verify_capability(cap: dict, repo: Path) -> dict:
    """Per-capability evidence verdict."""
    cid = cap.get("id")
    if cid is None:
        cid = "<unknown-id>"

    evidence = cap.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = []
    if not evidence:
        return {
            "status": "FAIL",
            "missing_files": [],
            "scope_missing": [],
            "detail": "no evidence",
        }

    missing_files: list[str] = []
    scope_missing: list[str] = []
    for entry in evidence:
        if not isinstance(entry, dict):
            missing_files.append("<invalid-entry>")
            continue
        m, s = _check_evidence_entry(entry, repo)
        missing_files.extend(m)
        scope_missing.extend(s)

    # Deduplicate while preserving first-seen order (deterministic).
    missing_files = list(dict.fromkeys(missing_files))
    scope_missing = list(dict.fromkeys(scope_missing))

    if missing_files:
        status, detail = "FAIL", f"missing file(s): {missing_files[:3]}"
    elif scope_missing:
        status = "FAIL"
        detail = f"scope not found in file(s): {scope_missing[:3]}"
    else:
        status, detail = "PASS", f"all {len(evidence)} evidence entries verified"

    return {
        "status": status,
        "missing_files": missing_files,
        "scope_missing": scope_missing,
        "detail": detail,
    }


def verify_evidence(package_or_capabilities, repo_dir) -> dict:
    """Verify evidence for every capability against real repo files.

    Input: a compiled package dict, an analyst_analysis dict (both having a
    'capabilities' key), a bare list of capabilities, or a single capability
    dict. repo_dir is a filesystem path (Path or str) to the repo root.

    Returns deterministic dict {cap_id: verdict} where verdict is
    {'status': 'PASS'|'FAIL', 'missing_files': [...], 'scope_missing': [...],
     'detail': str}.
    """
    repo = Path(repo_dir)
    results = {}
    for cap in _extract_capabilities(package_or_capabilities):
        cap = cap or {}  # tolerate None entries without crashing
        cid = cap.get("id") if cap.get("id") is not None else f"cap-{len(results)}"
        # keep unique keys: a dup id is suffixed (e.g. c1, c1-2) so no verdict
        # is silently overwritten
        base, n = cid, 2
        while cid in results:
            cid = f"{base}-{n}"
            n += 1
        results[cid] = _verify_capability(cap, repo)
    for cid, verdict in results.items():
        if verdict["status"] == "FAIL":
            LOG.warning("evidence FAIL cap=%s: %s", cid, verdict["detail"])
    LOG.info("evidence verified caps=%d", len(results))
    return results


def verify_package(package: dict, repo_dir) -> dict:
    """Aggregate gate: does the whole package's evidence verify?

    Returns {'ok': bool, 'results': {cap_id: verdict}}. ok is True iff every
    capability PASSes (or there are no capabilities).
    """
    results = verify_evidence(package, repo_dir)
    statuses = [v["status"] for v in results.values()]
    return {
        "ok": all(s == "PASS" for s in statuses) if statuses else True,
        "results": results,
    }