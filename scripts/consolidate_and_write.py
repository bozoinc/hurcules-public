#!/usr/bin/env python3
"""Apply capability consolidation to all 21 Stage 3 survivor sets.

Writes data/consolidated/<gold_id>.json with the merged candidate list.
Deterministic, no LLM. Usage: python3 scripts/consolidate_and_write.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from hurcules.consolidate import consolidate

S3 = ROOT / "data" / "stage3-analysis"
OUT = ROOT / "data" / "consolidated"
OUT.mkdir(parents=True, exist_ok=True)

total_before = total_after = 0
rows = []
for f in sorted(S3.glob("*.json")):
    if f.name.endswith(".judged.json"):
        continue
    gid = f.stem
    data = json.load(open(f))
    survivors = data.get("survivors", [])
    consolidated = consolidate(survivors)
    total_before += len(survivors)
    total_after += len(consolidated)
    out = OUT / f"{gid}.json"
    out.write_text(json.dumps(consolidated, indent=2, sort_keys=True) + "\n")
    rows.append((gid, len(survivors), len(consolidated)))

print(f"consolidation: {total_before} survivors -> {total_after} consolidated "
      f"(-{(1 - total_after/total_before)*100:.0f}%)")
for gid, b, a in rows:
    print(f"  {gid:20s} {b:3d} -> {a:3d}")