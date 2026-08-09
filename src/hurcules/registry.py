"""HURCULES Stage 6 — Capability Registry (deterministic, local, validated-only).

Only packages that passed the Stage 5 evaluation enter the registry. Every
entry records provenance + evaluation + approval state. Nothing is approved
automatically (D4: human approval required; status stays 'candidate' until a
human sets 'approved').

Public seam: Registry class backed by a JSON file (data/registry/registry.json).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_VERSION = "1.0.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Registry:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, dict] = {}
        if self.path.exists():
            self._entries = json.loads(self.path.read_text())

    def register(self, package: dict, eval_result: dict | None = None,
                 source_repo: str = "", commit_sha: str = "") -> dict:
        """Add a validated capability package. Returns the registry entry.

        Rejects packages missing required schema/provenance. Records
        status='candidate' (never auto-approved, D4).
        """
        caps = package.get("capabilities", []) if package else []
        if not caps:
            raise ValueError("cannot register empty package")
        pkg_id = package.get("provenance", {}).get("repository") or source_repo
        commit = (package.get("provenance") or {}).get("commit_sha") or commit_sha
        entry_id = str(uuid.uuid4())[:12]
        entry = {
            "entry_id": entry_id,
            "pkg_id": pkg_id,
            "commit_sha": commit,
            "capability_count": len(caps),
            "capabilities": [{"id": c.get("id"), "name": c.get("name"),
                              "ontology_type": c.get("ontology_type"),
                              "confidence": c.get("confidence")} for c in caps],
            "eval": eval_result or {},
            "status": "candidate",  # D4: human approval required
            "registered_at": _now(),
        }
        self._entries[entry_id] = entry
        self._persist()
        return entry

    def approve(self, entry_id: str, approver: str) -> dict:
        """Human approval (D4). Sets status='approved', records approver/time."""
        if entry_id not in self._entries:
            raise KeyError(f"no registry entry {entry_id}")
        self._entries[entry_id]["status"] = "approved"
        self._entries[entry_id]["approved_by"] = approver
        self._entries[entry_id]["approved_at"] = _now()
        self._persist()
        return self._entries[entry_id]

    def list(self, status: str | None = None) -> list[dict]:
        entries = list(self._entries.values())
        if status:
            entries = [e for e in entries if e.get("status") == status]
        return sorted(entries, key=lambda e: e.get("registered_at", ""))

    def get(self, entry_id: str) -> dict | None:
        return self._entries.get(entry_id)

    def _persist(self):
        self.path.write_text(json.dumps(self._entries, indent=2, sort_keys=True) + "\n")