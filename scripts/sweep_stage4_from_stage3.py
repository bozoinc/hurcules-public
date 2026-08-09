#!/usr/bin/env python3
"""Compile Stage 4 packages from existing Stage 3 analyses (no re-analysis).

For each data/stage3-analysis/<id>.json survivor set + Stage 2 baseline map,
run the compiler and write data/stage4-packages/<id>.json. Fast (no LLM).
Usage: python3 scripts/sweep_stage4_from_stage3.py [id1,id2,...]
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from hurcules.compiler import compile_package

S3 = ROOT / "data" / "stage3-analysis"
S2 = ROOT / "data" / "stage2-baseline"
OUT = ROOT / "data" / "stage4-packages"

only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
OUT.mkdir(parents=True, exist_ok=True)

results = []
for s3_file in sorted(S3.glob("*.json")):
    gid = s3_file.stem
    if only and gid not in only:
        continue
    s2_file = S2 / f"{gid}.json"
    if not s2_file.exists():
        print(f"[skip] {gid}: no stage2 baseline")
        continue
    try:
        analysis = json.load(open(s3_file))
        repo_map = json.load(open(s2_file))
        survivors = analysis.get("survivors", [])
        result = compile_package({"capabilities": survivors}, repo_map, repo_map.get("repository", gid))
        out = OUT / f"{gid}.json"
        out.write_text(json.dumps({"gold_id": gid, "compiled_from": "stage3-analysis", **result},
                                  indent=2, sort_keys=True) + "\n")
        tag = "OK" if result["ok"] else f"REJECTED({len(result['errors'])})"
        print(f"[compiled] {gid}: {tag} ({len(survivors)} caps)")
        results.append((gid, result["ok"]))
    except Exception as e:
        print(f"[error] {gid}: {e}")

print(f"\nstage4 compile sweep: {sum(1 for _,ok in results if ok)} OK, "
      f"{sum(1 for _,ok in results if not ok)} rejected out of {len(results)}")