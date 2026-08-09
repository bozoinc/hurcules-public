#!/usr/bin/env python3
"""Stage 2 baseline: run the deterministic mapper across all 21 gold repos.

Writes data/stage2-baseline/<gold_id>.json for each, plus a manifest index.
Deterministic: rerunning regenerates identical files.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from hurcules.mapper import map_repository

CLONES = {
    "archon": "~/projects/Archon",
    "mem0": "~/projects/mem0",
    "jq": "~/projects/gold-jq",
    "ripgrep": "~/projects/gold-ripgrep",
    "express": "~/projects/gold-express",
    "click": "~/projects/gold-click",
    "fd": "~/projects/gold-fd",
    "pytest": "~/projects/gold-pytest",
    "prettier": "~/projects/gold-prettier",
    "zx": "~/projects/gold-zx",
    "yq": "~/projects/gold-yq",
    "bat": "~/projects/gold-bat",
    "tokei": "~/projects/gold-tokei",
    "mattpocock-skills": "~/projects/gold-mattpocock-skills",
    "awesome-graph-eng": "~/projects/gold-awesome-graph-eng",
    "nolicense": "~/projects/gold-nolicense",
    "suspicious": "~/projects/gold-suspicious",
    "hexyl": "~/projects/gold-hexyl",
    "ratty": "~/projects/gold-ratty",
    "navi": "~/projects/gold-navi",
    "claimgap": "~/projects/gold-claimgap5",
}

OUT = ROOT / "data" / "stage2-baseline"
OUT.mkdir(parents=True, exist_ok=True)

manifest = {}
ok, failed = 0, 0
for gold_id, clone in CLONES.items():
    repo = os.path.expanduser(clone)
    if not os.path.isdir(repo):
        print(f"SKIP {gold_id}: no clone at {repo}")
        failed += 1
        continue
    try:
        m = map_repository(repo)
        out = OUT / f"{gold_id}.json"
        out.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")
        manifest[gold_id] = {
            "clone": clone,
            "file_count": m["file_count"],
            "languages": len(m["languages"]),
            "manifests": m["dependency_manifests"],
            "entry_points": m["entry_points"],
            "tests": len(m["test_files"]),
            "docs": len(m["documentation_files"]),
            "licenses": m["license_files"],
            "secret_locations": m["secret_file_locations"],
            "risk_flags": len(m["risk_flags"]),
        }
        ok += 1
    except Exception as e:
        print(f"ERROR {gold_id}: {e}")
        failed += 1

(OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(f"\nComplete: {ok} mapped, {failed} failed/skipped")
print(f"Baseline written to {OUT}/ ({len(os.listdir(OUT))} files)")