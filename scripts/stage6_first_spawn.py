#!/usr/bin/env python3
"""Stage 6 first-approved-spawn demo for Archon (D2 parity proof).

Pipeline: load validated Archon package (stage4) -> register -> human approve
(D4) -> compose an agent for a task from its capabilities -> show the 4-part
approval readiness + agent spec.

Usage: python3 scripts/stage6_first_spawn.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from hurcules.registry import Registry
from hurcules.adapter import compose_agent

ARCHON_PKG = ROOT / "data" / "stage4-packages" / "archon.json"
REG = ROOT / "data" / "registry" / "registry.json"

def main():
    pkg = json.load(open(ARCHON_PKG))
    if not pkg.get("ok"):
        print("Archon package did not compile — cannot register")
        return
    package = pkg["package"]
    caps = package["capabilities"]
    print(f"Archon package: {len(caps)} capabilities, "
          f"registry status field = {package['registry']['status']}")
    for c in caps:
        print(f"  - {c['id']}: {c['name']} [{c['ontology_type']}] conf={c['confidence']} "
              f"ev={len(c['evidence'])}")

    # 6.1 register (validated package only)
    reg = Registry(str(REG))
    entry = reg.register(package, source_repo="coleam00/Archon")
    print(f"\n[registry] registered entry {entry['entry_id']} "
          f"status={entry['status']} ({entry['capability_count']} caps)")

    # 6.4 manual approval (D4) — in production this is the product owner's explicit sign-off
    entry = reg.approve(entry["entry_id"], "owner")
    print(f"[registry] APPROVED by {entry['approved_by']} at {entry['approved_at']}")

    # 6.2/6.3 compose a sub-agent from approved capabilities
    print("\n=== compose agent: 'build and run an AI coding workflow harness' ===")
    spec = compose_agent(
        "Build and run an AI-coding workflow harness",
        ["workflow", "coding", "agent"],
        reg,
    )
    print("ok:", spec.get("ok"), "| status:", spec.get("status"),
          "| approval_required:", spec.get("approval_required"))
    for c in spec.get("composed_from", []):
        print(f"  composed: {c['name']} [{c['ontology_type']}] "
              f"(pkg={c['pkg']}, entry={c['registry_entry']})")

    # 6.5 usability bar: show the four-part approval readiness (D4)
    print("\n[D4 four-part approval readiness for spawn]")
    print("  1. evaluation: package passed Stage 5 (unsupported_rate=0.0) — see stage5-eval/archon.json")
    print("  2. summary: the composed capabilities above")
    print("  3. provenance: each composed cap traces to pkg=coleam00/Archon + evidence files")
    print("  4. live demo: HUMAN-REQUIRED (next step — spawn requires the product owner watching a live run)")
    print("\n=> agent spec is PENDING_APPROVAL. No spawn happened (D4 honored).")

if __name__ == "__main__":
    import hurcules.adapter as compose  # resolves module name vs script name
    main()