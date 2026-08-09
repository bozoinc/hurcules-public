"""HURCULES Stage 10 — Moat Asset Inventory (10.7).

Maps the real, durable assets the system accumulates so they can become a
defensible commercial moat (commercial-intent strategy):

  - ontology          : capability ontology (gold + stage4 package knowledge)
  - evaluation_corpus  : stage5 eval verdicts (holdout for anti-overfit)
  - provenance data    : registry entries (approved caps, committed provenance)
  - adapters           : discovery/rank/clone logic (Stage 8)

The inventory is autofed from the actual data tree (glob), deterministic, cheap.
It deliberately reports capability counts as facts — NOT as a vanity "template
success" metric (SUB-GOALS: template count != success).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

MOAT_VERSION = "1.0.0"
_PATHS = {
    "registry": "data/registry/registry.json",
    "eval": "data/stage5-eval",
    "packages": "data/stage4-packages",
    "gold": "data/gold",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def inventory(root: Path, *, high_value: list[str] | None = None) -> dict:
    """Return the moat-asset inventory for the repo's data tree."""
    registry_entries = []
    reg_path = root / _PATHS["registry"]
    if reg_path.exists():
        try:
            registry_entries = list(json.loads(reg_path.read_text()).values())
        except json.JSONDecodeError:
            registry_entries = []

    def _glob(sub: str, ext: str) -> list[Path]:
        d = root / _PATHS[sub]
        return sorted(d.glob(f"*.{ext}")) if d.exists() else []

    eval_files = _glob("eval", "json")
    pkg_files = _glob("packages", "json")
    gold_files = _glob("gold", "yaml")

    approved = [e for e in registry_entries if e.get("status") == "approved"]
    total_caps = sum(len(e.get("capabilities", [])) for e in registry_entries)
    approved_caps = sum(len(e.get("capabilities", [])) for e in approved)

    assets = {
        "ontology_repos": sorted({e.get("pkg_id") for e in registry_entries if e.get("pkg_id")}),
        "evaluation_corpus": [p.name for p in eval_files],
        "gold_corpus": [p.stem for p in gold_files],
        "validated_packages": [p.name for p in pkg_files],
        "approved_registry_entries": len(approved),
        "total_capabilities": total_caps,
        "approved_capabilities": approved_caps,
    }
    if high_value:
        assets["high_value_assets"] = high_value

    return {
        "schema": "hurcules.moat-inventory-v1",
        "moat_version": MOAT_VERSION,
        "generated_at": _now(),
        "assets": assets,
    }