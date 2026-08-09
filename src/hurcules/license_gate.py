"""HURCULES license-compliance GATE (deterministic, no LLM, no network).

The mapper detects license FILE NAMES; this gate parses license POSTURE.
Pure stdlib + Path reads: same input repo => same verdict every run.

Public seams:
  detect_license(repo_dir)          -> dict
  check_license(repo_dir, marketplace=False) -> dict
"""
from __future__ import annotations

from pathlib import Path

from hurcules.logutil import get_logger

LICENSE_GATE_VERSION = "1.0.0"

LOG = get_logger(__name__)

# File-name stems (lowercased, extension stripped) that count as a license.
_LICENSE_STEMS = {"license", "licence", "copying", "unlicense", "copyright"}

# (marker, status, license_name, variant_hint) in priority order.
# Permissive/copyleft markers are checked BEFORE proprietary ones so a classic
# "Copyright (c) ... All rights reserved." header above an MIT body still
# scores permissive instead of proprietary.
_MARKERS = [
    # --- permissive ----------------------------------------------------
    ("permission is hereby granted, free of charge", "permissive", "MIT", None),
    ("this is free and unencumbered software released into the public domain",
     "permissive", "Unlicense", None),
    ("unlicense", "permissive", "Unlicense", None),
    ("apache license", "permissive", "Apache-2.0", None),
    ("apache", "permissive", "Apache-2.0", None),
    # BSD family — 3-Clause adds the "neither the name" / "endorse" clause.
    ("redistribution and use in source and binary forms", "permissive",
     "BSD-3-Clause", "bsd3"),
    ("redistributions of source code must retain", "permissive",
     "BSD-3-Clause", "bsd3"),
    # ISC and Zlib
    ("isc license", "permissive", "ISC", None),
    ("permission to use, copy, modify, and/or distribute", "permissive", "ISC", None),
    ("zlib license", "permissive", "Zlib", None),
    ("altered source versions must be plainly marked", "permissive", "Zlib", None),
    # --- copyleft ------------------------------------------------------
    ("affero", "copyleft", "AGPL", None),
    ("gnu lesser general public license", "copyleft", "LGPL", None),
    ("lesser general public license", "copyleft", "LGPL", None),
    ("gnu general public license", "copyleft", "GPL", None),
    ("mozilla public license", "copyleft", "MPL-2.0", None),
    ("mpl-2.0", "copyleft", "MPL-2.0", None),
    # --- proprietary (only reached when no known license matched) ------
    ("all rights reserved", "proprietary", "proprietary", None),
    ("proprietary", "proprietary", "proprietary", None),
    ("no license granted", "proprietary", "proprietary", None),
    ("personal use only", "proprietary", "proprietary", None),
]

# Version disambiguation for GPL-family names (checked on the raw text).
_GPL_VERSION_MARKERS = [
    ("gpl-3", "GPL-3.0"), ("gplv3", "GPL-3.0"), ("gnu gpl v3", "GPL-3.0"),
    ("version 3", "GPL-3.0"),
    ("gpl-2", "GPL-2.0"), ("gplv2", "GPL-2.0"), ("gnu gpl v2", "GPL-2.0"),
    ("version 2", "GPL-2.0"),
]

def _is_license_filename(name: str) -> bool:
    """True if `name` looks like a license file (case-insensitive)."""
    low = name.lower()
    stem = low
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    if stem in _LICENSE_STEMS:
        return True
    return stem.startswith(("license-", "licence-", "copying"))


def _read_text(path: Path) -> str | None:
    """Read a license file as utf-8 text; None on any read/decoding error."""
    try:
        if path.stat().st_size > 2_000_000:  # don't slurp giant junk files
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _classify(text: str) -> tuple[str, str | None]:
    """classify license text -> (status, license_name). Deterministic."""
    low = text.lower()
    for marker, status, lic_name, hint in _MARKERS:
        if marker in low:
            if hint == "bsd3" and "neither the name" in low:
                lic_name = "BSD-3-Clause"
            elif hint == "bsd3":
                lic_name = "BSD-2-Clause"
            if status == "copyleft" and lic_name == "GPL":
                for vm, vname in _GPL_VERSION_MARKERS:
                    if vm in low:
                        lic_name = vname
                        break
            return status, lic_name
    return "unknown", None


def _find_license_files(repo_dir: str) -> list[Path]:
    """Deterministically ordered license-file candidates (shallow first,
    then alphabetically) with a relative-path tiebreak for stability."""
    root = Path(repo_dir)
    cands = []
    for p in root.rglob("*"):
        if p.is_file() and _is_license_filename(p.name):
            rel = p.relative_to(root)
            cands.append((len(rel.parts), p.name.lower(), rel.as_posix(), p))
    cands.sort(key=lambda t: (t[0], t[1], t[2]))
    return [c[3] for c in cands]


def detect_license(repo_dir: str) -> dict:
    """Detect + classify the repo's license posture. Pure fs reads, no LLM.

    Returns: {'status', 'file', 'license_name'}
      status: 'permissive' | 'copyleft' | 'proprietary' | 'unknown' | 'none'
      file:  relative path of the license file that drove the verdict (or None)
      license_name: recognized SPDX-ish name (MIT, GPL-3.0, ...) or None

    When multiple license files exist, the first (shallowest, alphabetically)
    file that classifies to a KNOWN license wins; the file is reported in
    `file` relative to repo_dir.
    """
    root = Path(repo_dir)
    if not root.is_dir():
        raise ValueError(f"not a directory: {repo_dir}")

    for p in _find_license_files(repo_dir):
        text = _read_text(p)
        if text is None:
            continue
        status, lic_name = _classify(text)
        if status != "unknown":
            LOG.info("detect repo=%s status=%s name=%s file=%s",
                     repo_dir, status, lic_name, p.name)
            return {
                "status": status,
                "file": p.relative_to(root).as_posix(),
                "license_name": lic_name,
            }

    check = _check_no_classifiable(root)
    return check


def _check_no_classifiable(root: Path) -> dict:
    """Fallback when no license file classifies: report the first file as
    unknown, or 'none' when there is no license file at all."""
    found = [p for p in root.rglob("*")
             if p.is_file() and _is_license_filename(p.name)]
    if found:
        first = sorted(found, key=lambda p: p.name.lower())[0]
        return {"status": "unknown",
                "file": first.relative_to(root).as_posix(),
                "license_name": None}
    return {"status": "none", "file": None, "license_name": None}


def check_license(repo_dir: str, marketplace: bool = False) -> dict:
    """License-compliance gate the compiler/product layer calls.

    Rules:
      proprietary / unknown  -> blocked always ('non-compliant license')
      none                   -> blocked ONLY when marketplace=True
                                ('no license — cannot distribute'); allowed
                                for non-distribution (analysis-only)
      permissive / copyleft  -> allowed; copyleft adds a 'copyleft': True
                                warning so callers can surface it

    Returns: {'ok', 'status', 'blocked_reason', 'file', 'license_name'}
      (plus 'copyleft': True when the license is copyleft)
    """
    det = detect_license(repo_dir)
    status = det["status"]
    blocked_reason = None
    if status in ("proprietary", "unknown"):
        blocked_reason = "non-compliant license"
    elif status == "none" and marketplace:
        blocked_reason = "no license — cannot distribute"

    result = {
        "ok": blocked_reason is None,
        "status": status,
        "blocked_reason": blocked_reason,
        "file": det["file"],
        "license_name": det["license_name"],
    }
    if status == "copyleft":
        result["copyleft"] = True
    LOG.info("check repo=%s marketplace=%s status=%s ok=%s",
             repo_dir, marketplace, status, result["ok"])
    return result