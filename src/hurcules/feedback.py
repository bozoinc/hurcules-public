"""HURCULES W3-[9] — Feedback Recorder (deterministic, local, no LLM).

The D5 spawn loop's missing half: a capability/spawn is evaluated or flagged
in use, and the outcome (pass rate, usage, edge cases, flags) must be written
BACK to the originating capability package so the package becomes a living
record instead of a static snapshot.

Everything is pure stdlib + JSON, mirroring the registry.py JSON-store
pattern: ``record_feedback`` appends a record to a JSON file keyed by
capability_id -> list of records. ``summarize`` folds that history into a
deterministic, division-safe summary; ``attach_to_package`` copies a package
dict and adds the summary under a top-level ``feedback`` key without mutating
the original.

Public seam:
  record_feedback(store_path, record)      -> None
  package_feedback_history(store_path, capability_id) -> list[dict]
  summarize(store_path, capability_id)     -> dict
  attach_to_package(package_dict, store_path, capability_id) -> dict
"""
from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_VERSION = "1.0.0"

VALID_EVENTS = {"spawn", "eval", "flag"}
VALID_OUTCOMES = {"pass", "fail", "flag"}


@dataclass
class FeedbackRecord:
    """One recorded outcome for a capability in use.

    capability_id — which capability was evaluated/spawned/flagged.
    package_id    — which package it originated from (registry provenance).
    event         — 'spawn' | 'eval' | 'flag'.
    outcome       — 'pass' | 'fail' | 'flag'  (flags carry 'flag'/'flag').
    detail        — free-text note (e.g. an edge case description).
    ts            — ISO timestamp; defaults to now (UTC).
    source        — where the feedback came from, e.g. 'fleet-run-abc'.
    """
    capability_id: str
    package_id: str
    event: str
    outcome: str
    detail: str = ""
    ts: str = ""
    source: str = ""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(store_path: Path) -> dict[str, list[dict]]:
    if not store_path.exists():
        return {}
    try:
        data = json.loads(store_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _validate(record: FeedbackRecord) -> None:
    if not getattr(record, "capability_id", ""):
        raise ValueError("feedback record requires capability_id")
    if record.event not in VALID_EVENTS:
        raise ValueError(f"unknown event '{record.event}', expected one of "
                         f"{sorted(VALID_EVENTS)}")
    if record.outcome not in VALID_OUTCOMES:
        raise ValueError(f"unknown outcome '{record.outcome}', expected one of "
                         f"{sorted(VALID_OUTCOMES)}")


def _finalize(record: FeedbackRecord) -> dict:
    """Validate + fill defaults, return a plain dict ready for storage."""
    _validate(record)
    if not record.ts:
        record.ts = _now()
    if not record.source:
        record.source = "hurcules"
    return asdict(record)


def record_feedback(feedback_store: str | Path, record: FeedbackRecord) -> None:
    """Append ``record`` to the feedback store and persist deterministically.

    The store is a JSON file: {capability_id: [record, ...]}. Missing paths
    are created (parents too). Existing history for the capability is kept and
    the new record appended, then sorted by ts before writing.
    """
    path = Path(feedback_store)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _load(path)
    entry = _finalize(record)
    cap = entry["capability_id"]
    records = data.get(cap, [])
    records.append(entry)
    data[cap] = sorted(records, key=lambda r: r["ts"])
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def package_feedback_history(store_path: str | Path,
                             capability_id: str) -> list[dict]:
    """Return all records for ``capability_id``, sorted by timestamp.

    Unknown capabilities and empty/missing stores return [].
    """
    data = _load(Path(store_path))
    return sorted(data.get(capability_id, []), key=lambda r: r["ts"])


def summarize(store_path: str | Path, capability_id: str) -> dict:
    """Fold a capability's feedback history into a deterministic summary.

    Returns:
      events      — total records.
      pass_rate   — pass-outcome events / total (0.0 when there are none,
                    so empty history never division-by-zero errors).
      flags       — [detail] for every flag event.
      usages      — number of 'spawn' events.
      edge_cases  — [detail] for every record whose outcome == 'flag'.
    """
    history = package_feedback_history(store_path, capability_id)
    total = len(history)
    passed = sum(1 for r in history if r.get("outcome") == "pass")
    pass_rate = round(passed / total, 4) if total else 0.0
    flags = [r.get("detail", "")
             for r in history
             if r.get("event") == "flag" and r.get("detail")]
    spawns = sum(1 for r in history if r.get("event") == "spawn")
    edge_cases = [r.get("detail", "")
                  for r in history
                  if r.get("outcome") == "flag" and r.get("detail")]
    return {
        "events": total,
        "pass_rate": pass_rate,
        "flags": flags,
        "usages": spawns,
        "edge_cases": edge_cases,
    }


def attach_to_package(package_dict: dict, store_path: str | Path,
                      capability_id: str) -> dict:
    """Return a deep copy of ``package_dict`` with a top-level ``feedback`` key.

    ``feedback`` holds the summarize() output for ``capability_id``, so a
    registry package carries its living history. The input dict is never
    mutated; deterministic (identical history -> identical copy).
    """
    out = copy.deepcopy(package_dict)
    out["feedback"] = summarize(store_path, capability_id)
    return out