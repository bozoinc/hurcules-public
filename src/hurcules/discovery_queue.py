"""HURCULES Stage 8.4 — discovery queue: dedupe + allow/deny + budget.

Sweep control for discovery. Re-sweeping re-clones and re-analyzes repos we
already ingested (waste) or already failed (repeat failures). This module
lets a sweep:

  - skip repos with a known outcome (status done/failed),
  - honour allow/deny lists,
  - cap how many repos one sweep may run (budget).

Deterministic, stdlib only, no network.

State file: JSON map {repo: {"status": ..., "at": ...}} where status is one
of 'queued' | 'done' | 'failed' | 'skipped'.
  - done / failed    -> known outcome, never re-run.
  - queued / skipped -> may be planned again.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STATUS_QUEUED = "queued"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

# Statuses with a known outcome: re-running them is pure waste.
KNOWN = frozenset({STATUS_DONE, STATUS_FAILED})


@dataclass
class QueueState:
    """One repo's queue record: {repo, status, at}.

    status is one of 'queued' | 'done' | 'failed' | 'skipped'.
    at is the ISO timestamp the status was recorded (UTC).
    """

    repo: str
    status: str = STATUS_QUEUED
    at: str = ""

    def to_dict(self) -> dict:
        return {"repo": self.repo, "status": self.status, "at": self.at}


def load_state(store_path) -> dict[str, dict]:
    """Read {repo: {status, at}} from a JSON file. Missing file -> {}."""
    p = Path(store_path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        # Corrupt/unreadable state must never crash a sweep: treat as empty.
        return {}
    return data if isinstance(data, dict) else {}


def mark(store_path, repo: str, status: str) -> None:
    """Upsert repo's status and persist the state (sorted, deterministic)."""
    state = load_state(store_path)
    state[repo] = {"status": status, "at": _now()}
    _save(store_path, state)


def _save(store_path, state: dict) -> None:
    p = Path(store_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_name(c) -> str:
    """Repo identifier from a dict (with 'repo' key) or object (.repo attr)."""
    if isinstance(c, dict):
        return c["repo"]
    return c.repo


def filter_candidates(candidates, state, allow=None, deny=None) -> list:
    """Filter candidates down to the ones a sweep may run.

    - drops repos already in `state` with status done/failed (known outcome),
    - allow: if non-empty, ONLY these repos are kept,
    - deny: these repos are never kept.
    Input order is preserved. `candidates` may be dicts with a 'repo' key
    or objects with a `.repo` attribute (e.g. discovery.Candidate).
    """
    out = []
    for c in candidates:
        repo = _repo_name(c)
        entry = state.get(repo)
        if entry and entry.get("status") in KNOWN:
            continue
        if allow and repo not in allow:
            continue
        if deny and repo in deny:
            continue
        out.append(c)
    return out


def plan_sweep(candidates, state, budget=None) -> dict:
    """Plan a sweep: what to run, what was skipped, whether budget cut in.

    Only state-based skipping is counted here; allow/deny is a separate
    filter step (filter_candidates) so plan_sweep's skipped_allow_deny is 0.
    `budget` caps to_run (truncation keeps input order).
    """
    to_run = []
    skipped_done = 0
    skipped_failed = 0
    for c in candidates:
        repo = _repo_name(c)
        entry = state.get(repo)
        if entry and entry.get("status") == STATUS_DONE:
            skipped_done += 1
            continue
        if entry and entry.get("status") == STATUS_FAILED:
            skipped_failed += 1
            continue
        to_run.append(c)

    budget_used = False
    if budget is not None and len(to_run) > budget:
        to_run = to_run[:budget]
        budget_used = True
    return {
        "to_run": to_run,
        "skipped_done": skipped_done,
        "skipped_failed": skipped_failed,
        "skipped_allow_deny": 0,
        "budget_used": budget_used,
    }


def per_repo_timeout(repo: str, base: int = 120, extra_per_file: int = 0) -> int:
    """Per-repo clone/ingest timeout in seconds.

    KISS deterministic default: base plus any per-file allowance. The
    extra_per_file seam exists so a caller can scale cost by repo size
    (e.g. mapped file count) without changing call sites.
    """
    return base + extra_per_file
