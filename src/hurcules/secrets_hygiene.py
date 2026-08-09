"""HURCULES W2-[8] — deterministic secrets-hygiene scan + registry gate.

The pilot found a real failure mode: sharkdp/hexyl's ``.github/workflows/
CICD.yml`` was flagged ``secret-reference`` by the mapper. Downstream stages
then reasoned about "secrets" from a location name alone, and a sloppy stage
COULD copy a secret VALUE into the capability package. This module makes that
impossible and turns the hexyl case into a permanent, deterministic regression:

1. ``scan_secrets(repo_dir)``   — deterministic repo walk. Reports WHERE secret
   VALUES live (pattern names + file paths only) plus location names and
   reference sites. NEVER returns the matched values themselves (anti-leak).
2. ``verify_no_values_in_package(package)`` — hard gate walked over a parsed
   package dict before it may enter the registry. False kills the package.

Public seam:
  scan_secrets(repo_dir) -> dict
  verify_no_values_in_package(package_dict) -> bool
  regression_case_hexyl_cicd() -> str   (YAML fixture, no network)
  find_secret_values(text) -> list[str] (pattern names, never values)
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from hurcules.logutil import get_logger

LOG = get_logger(__name__)

SCAN_VERSION = "1.0.0"

# Secret VALUE formats. Each entry: (pattern name, regex source). The name is
# all we ever surface downstream — matching VALUES are never returned.
SECRET_VALUE_PATTERNS = [
    ("github-token", r"\bghp_[0-9A-Za-z]{36}\b"),
    ("openai-key", r"\bsk-[A-Za-z0-9]{20,}\b"),
    ("aws-access-key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("slack-token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    ("private-key", r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    ("password-assignment", r"\bpassword\s*[:=]\s*\S+"),
]

# Reference words mirror mapper.SECRET_REF_WORDS (kept local so this module is
# independent of files owned by sibling tasks). A file containing one of these
# tokens is a REFERENCE site, never reported as a leaked value.
SECRET_REF_WORDS = ["api_key", "api-key", "private_key", "access_token", "secret"]

# Secret-LOOKING file names (locations only — a real value inside is still
# caught by the value scan, unlike the mapper which never reads them).
SECRET_FILE_NAMES = {".env", ".env.local", "id_rsa", "id_dsa", "id_ed25519",
                     "credentials", "secrets", "secret"}

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
             "build", ".tox", ".pytest_cache", "target", ".svn", ".hg", ".idea"}

MAX_FILE_SIZE = 500_000  # bytes; matches mapper's size cap

_COMPILED = [
    (name, re.compile(src, re.IGNORECASE if name == "password-assignment" else 0))
    for name, src in SECRET_VALUE_PATTERNS
]


def find_secret_values(text: str) -> list[str]:
    """Return sorted, deduped pattern NAMES present in ``text``.

    Anti-leak invariant: returns e.g. ``["github-token"]``, never the matched
    value itself. Callers may print/emit this result freely.
    """
    found = [name for name, pat in _COMPILED if pat.search(text)]
    return sorted(found)


def scan_secrets(repo_dir: str) -> dict:
    """Deterministic secrets-hygiene scan of a repository.

    Walks every file (skipping SKIP_DIRS, size cap MAX_FILE_SIZE, binary
    guard) and reports:

      value_hits             — [{"file": rel, "found": [pattern names]}] where
                                a secret VALUE matched; values never included.
      secret_file_locations  — sorted file names that look like secret files
                                (.env, id_rsa, ...).
      references             — sorted files whose text contains SECRET_REF_WORDS
                                tokens (e.g. ``${{ secrets.X }}``).

    All lists are sorted; identical input => identical output.
    """
    root = Path(repo_dir)
    if not root.is_dir():
        raise ValueError(f"not a directory: {repo_dir}")

    value_hits: list[dict] = []
    secret_locs: list[str] = []
    references: list[str] = []
    files_scanned = 0

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for fn in sorted(filenames):
            rel = (Path(dirpath).relative_to(root) / fn).as_posix()
            if fn.lower() in SECRET_FILE_NAMES:
                secret_locs.append(rel)
            full = root / rel
            try:
                if not full.is_file():
                    continue
                if full.stat().st_size > MAX_FILE_SIZE:
                    continue
                data = full.read_bytes()
                if b"\x00" in data[:8192]:
                    continue  # binary
                text = data.decode("utf-8", errors="ignore")
            except OSError:
                continue
            files_scanned += 1
            names = find_secret_values(text)
            if names:
                value_hits.append({"file": rel, "found": names})
            if any(w in text.lower() for w in SECRET_REF_WORDS):
                references.append(rel)

    LOG.info("secrets scan complete dir=%s scanned=%d hits=%d refs=%d",
             str(root), files_scanned, len(value_hits), len(references))
    return {
        "schema": "hurcules.secrets-hygiene",
        "schema_version": SCAN_VERSION,
        "files_scanned": files_scanned,
        "value_hits": sorted(value_hits, key=lambda h: h["file"]),
        "secret_file_locations": sorted(secret_locs),
        "references": sorted(references),
    }


def verify_no_values_in_package(package: dict) -> bool:
    """Hard gate: True iff ``package`` (parsed JSON) contains no secret VALUE.

    Walks the full nested structure (dicts / lists / strings) and runs every
    SECRET_VALUE_PATTERNS against each leaf string. Any match => False, so a
    package embedding ``ghp_...`` / ``sk-...`` / an AKIA id / ... cannot reach
    the registry. Location names and reference tokens are allowed (they carry
    no value); only VALUES trip the gate.
    """
    for leaf in _iter_strings(package):
        for _name, pat in _COMPILED:
            if pat.search(leaf):
                return False
    return True


def _iter_strings(obj):
    """Yield every string leaf of a parsed-JSON object (dict or list)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_strings(v)


HEXYL_CICD_FIXTURE = """\
name: CI/CD

on:
  push:
    branches: [master]
  pull_request: {}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: cargo build --release
      - run: cargo test

  release:
    runs-on: ubuntu-latest
    needs: test
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - uses: actions/checkout@v2
      - name: Push tag
        run: |
          curl -X POST \\
            -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \\
            -H "Accept: application/vnd.github.v3+json" \\
            https://api.github.com/repos/sharkdp/hexyl/releases
"""

# Stable digest of HEXYL_CICD_FIXTURE — guards accidental edits that would
# silently weaken the permanent regression fixture.
HEXYL_CICD_FIXTURE_SHA256 = "2461732ee91b8f79f45c566f1484a5f13428239501633905f20fdf41b240577c"


def regression_case_hexyl_cicd() -> str:
    """YAML fixture mirroring sharkdp/hexyl .github/workflows/CICD.yml.

    Contains a ``${{ secrets.GITHUB_TOKEN }}`` REFERENCE (must be flagged as a
    reference, never as a leaked value). Deterministic, no network.
    """
    return HEXYL_CICD_FIXTURE


def _fixture_digest() -> str:
    return hashlib.sha256(HEXYL_CICD_FIXTURE.encode("utf-8")).hexdigest()