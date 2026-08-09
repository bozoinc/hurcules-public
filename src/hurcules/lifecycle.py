"""HURCULES Stage 6 addendum — registry lifecycle states + stale detection.

Extends hurcules.registry.Registry WITHOUT modifying it. Entries get the
full lifecycle state machine (candidate -> approved -> deprecated /
revoked / superseded) plus stale detection when the upstream commit_sha
changes. Storage note: registry.get(entry_id) returns the live entry dict
(Registry keeps the same object in its internal _entries dict), so entries
are mutated in place and persisted via registry._persist() when present.
"""
from __future__ import annotations

from datetime import datetime, timezone

# Every legal state an entry can occupy.
VALID_STATES = {"candidate", "approved", "deprecated", "revoked", "superseded"}

# States that are still "live" (only live entries can be stale).
LIVE_STATES = {"candidate", "approved"}

# Allowed state transitions: nothing can leave revoked/superseded, and
# nothing can go backwards to candidate/approved.
ALLOWED_TRANSITIONS = {
    "candidate": {"approved", "deprecated", "revoked", "superseded"},
    "approved": {"deprecated", "revoked", "superseded"},
    "deprecated": {"revoked", "superseded"},
    "revoked": set(),
    "superseded": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_stale(entry: dict, current_commit_sha: str) -> bool:
    """True when a live entry points at an old upstream commit."""
    if entry.get("status") not in LIVE_STATES:
        return False  # stale only matters while the entry is live
    return entry.get("commit_sha") != current_commit_sha


def list_by_state(registry, state: str) -> list[dict]:
    """All entries currently in the given state (registry.list filter)."""
    return registry.list(status=state) if state else registry.list()


def mark_stale(entry_id: str, current_commit_sha: str, by: str, registry) -> dict:
    """Deprecate a stale live entry. Returns the entry (unchanged if fresh)."""
    manager = LifecycleManager(registry)
    entry = manager._entry(entry_id)
    if not is_stale(entry, current_commit_sha):
        return entry
    old = entry.get("commit_sha", "")
    reason = f"upstream commit changed: {old}->{current_commit_sha}"
    return manager.transition(entry_id, "deprecated", by, reason)


class LifecycleManager:
    """State machine for registry entries, built on a Registry instance."""

    def __init__(self, registry):
        self._registry = registry
        # Registry persists via _persist(); fall back gracefully if absent.
        self._persist_fn = getattr(registry, "_persist", None)

    def _entry(self, entry_id: str) -> dict:
        entry = self._registry.get(entry_id)
        if entry is None:
            raise KeyError(f"no registry entry {entry_id}")
        return entry

    def _persist(self):
        if callable(self._persist_fn):
            self._persist_fn()

    def transition(self, entry_id: str, new_state: str, by: str,
                   reason: str) -> dict:
        """Move an entry to new_state. Raises ValueError on invalid moves.

        Records {state, by, reason, at} in the entry's audit_trail.
        Returns the updated entry dict.
        """
        if new_state not in VALID_STATES:
            raise ValueError(f"invalid state: {new_state}")
        entry = self._entry(entry_id)
        old_state = entry.get("status")
        if old_state not in VALID_STATES:
            raise ValueError(f"unknown current state {old_state!r}: no transitions allowed")
        if new_state not in ALLOWED_TRANSITIONS.get(old_state, set()):
            raise ValueError(f"cannot transition {old_state} -> {new_state}")

        entry["status"] = new_state
        trail = entry.setdefault("audit_trail", [])
        trail.append({"state": new_state, "by": by, "reason": reason, "at": _now()})
        self._persist()
        return entry