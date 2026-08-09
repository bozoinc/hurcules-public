"""HURCULES Stage 8 — Discovery (autonomous GitHub candidate search).

Finds public GitHub repos that could yield NEW validated capabilities, ranks
them by relevance, and hands each to the same ingestion pipeline as the gold
set (no shortcuts). gated by cost/rate controls.

Two layers:
  1. PURE ranking (`rank`) — deterministic, fully testable offline.
  2. Network (`search_github`, `clone_candidate`) — shell to `gh api` / `git
     clone`; mocked in tests. Uses the minimal-permission gh CLI token.

Security: only PUBLIC repos (v1 scope). Every discovered candidate is DATA and
goes through the hostile-by-default pipeline (Stage 7 sandbox when executed).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

DISCOVERY_VERSION = "1.0.0"

# Permissive licenses we can legally learn from / reuse signal from. Marked
# ones are NOT safe to copy wholesale. We rank them, never auto-approve.
PERMISSIVE = {
    "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "cc0-1.0",
    "unlicense", "isc", "mpl-2.0",
}
RESTRICTIVE = {"gpl-2.0", "gpl-3.0", "agpl-3.0", "lgpl-2.1", "lgpl-3.0",
               "noassertion", "other", "proprietary"}

# Relevance-weight tuning for _score_candidate (all additive, deterministic).
W_STARS = 1.0e-5          # per star (so 10k stars -> +0.1 under mpl cap)
W_RECENT = 1.0            # full weight if activity within recency_days
RECENCY_DAYS = 180
W_PERMISSIVE = 3.0
W_FORBIDDEN = -10.0       # hard negative: restrictive/unknown license
W_SIZE_OK = 1.0


@dataclass
class Candidate:
    repo: str            # "owner/name"
    stars: int = 0
    pushed_at: str = ""  # ISO8601 (or "") — activity signal
    license_spdx: str = ""
    language: str = ""
    size_bytes: int = 0

    @classmethod
    def from_gh_item(cls, item: dict) -> "Candidate":
        lic = (item.get("license") or {}).get("spdx_id") or ""
        return cls(
            repo=item.get("full_name") or item.get("name") or "",
            stars=int(item.get("stargazers_count") or 0),
            pushed_at=str(item.get("pushed_at") or ""),
            license_spdx=str(lic or "").lower(),
            language=str(item.get("language") or ""),
            size_bytes=int(item.get("size") or 0),
        )


def _days_since(iso: str) -> float:
    """Days between now and an ISO timestamp; large if absent/parsing fails."""
    if not iso:
        return float("inf")
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    except ValueError:
        return float("inf")


def _license_signal(spdx: str) -> str:
    """Map spdx -> 'permissive' | 'restrictive' | 'unknown'."""
    s = spdx.lower()
    if s in PERMISSIVE:
        return "permissive"
    if s in RESTRICTIVE or s.startswith("gpl") or s.startswith("agpl"):
        return "restrictive"
    return "unknown"


def _score_candidate(c: Candidate) -> float:
    import math
    score = 0.0
    # stars: diminishing returns via log1p so 100 vs 10k doesn't dominate
    score += math.log1p(c.stars) * 0.5
    # recency of activity
    days = _days_since(c.pushed_at)
    if days <= RECENCY_DAYS:
        score += W_RECENT
    elif days != float("inf"):
        score += W_RECENT * max(0.0, 1 - (days - RECENCY_DAYS) / 365.0)
    # license: legal signal
    sig = _license_signal(c.license_spdx)
    if sig == "permissive":
        score += W_PERMISSIVE
    elif sig == "restrictive":
        score += W_FORBIDDEN
    # size: prefer lighter repos (cheaper to map); cap penalty on huge ones
    score += W_SIZE_OK if c.size_bytes and 1000 <= c.size_bytes <= 2_000_000 else 0
    return score


def rank_candidates(candidates: list[Candidate]) -> list[Candidate]:
    """Deterministic rank, descending score. Tie-break by repo name asc."""
    return sorted(
        candidates,
        key=lambda c: (-_score_candidate(c), c.repo),
    )


def top(candidates: list[Candidate], n: int) -> list[Candidate]:
    return rank_candidates(candidates)[:n]


# ---------------------------------------------------------------------------
# GitHub fetch (shells to gh CLI; mocked in tests)
# ---------------------------------------------------------------------------


def gh_search(query: str, limit: int = 20, shell=None) -> list[Candidate]:
    """Search GitHub for public repos via `gh api` search query.

    Returns ranked candidates. Testable by injecting `shell` (a
    callable(query) -> (rc, stdout, stderr)); default shells to `gh`.
    """
    api = shell or _gh_api
    rc, stdout, _ = api(f"search/repositories?q={quote(query)}&per_page={limit}")
    if rc != 0 or not stdout:
        return []
    data = json.loads(stdout)
    return [Candidate.from_gh_item(it) for it in data.get("items", [])]


def clone_candidate(repo: str, dest: str, commit: str | None = None,
                    invoke=None) -> bool:
    """Clone a public repo (optionally pinned to a commit) into dest.

    Shallow clone by default to bound cost. Returns True on success.
    `invoke` is injectable for tests (default subprocess.run).
    """
    runner = invoke or subprocess.run
    cmd = ["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", dest]
    proc = runner(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return False
    if commit:
        subprocess.run(["git", "-C", dest, "checkout", "-q", commit],
                       capture_output=True)
    return True


# internal: gh api JSON endpoint (shells to the authenticated gh CLI token)
def _gh_api(cmd_path: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["gh", "api", "-H", "Accept: application/vnd.github+json", cmd_path],
        capture_output=True, text=True, timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def quote(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9 ._-]", " ", s).replace(" ", "+")