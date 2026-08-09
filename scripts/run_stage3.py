#!/usr/bin/env python3
"""Run Stage 3 analyst + devil's advocate against a gold repo via OmniRoute.

Usage: python3 scripts/run_stage3.py <gold_id>
Reads data/stage2-baseline/<gold_id>.json, calls analyst + advocate, prints result.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from hurcules.mapper import map_repository
from hurcules.analyst import analyze, make_openai_client
from hurcules.devils_advocate import challenge

GOLD_ID = sys.argv[1] if len(sys.argv) > 1 else "jq"
CLONES = {
    "jq": "~/projects/gold-jq", "fd": "~/projects/gold-fd",
    "ratty": "~/projects/gold-ratty", "navi": "~/projects/gold-navi",
    "hexyl": "~/projects/gold-hexyl", "click": "~/projects/gold-click",
    "yq": "~/projects/gold-yq", "claimgap": "~/projects/gold-claimgap5",
    "nolicense": "~/projects/gold-nolicense",
    "archon": "~/projects/Archon", "mem0": "~/projects/mem0",
    "ripgrep": "~/projects/gold-ripgrep", "express": "~/projects/gold-express",
    "pytest": "~/projects/gold-pytest", "prettier": "~/projects/gold-prettier",
    "zx": "~/projects/gold-zx", "bat": "~/projects/gold-bat",
    "tokei": "~/projects/gold-tokei",
    "mattpocock-skills": "~/projects/gold-mattpocock-skills",
    "awesome-graph-eng": "~/projects/gold-awesome-graph-eng",
    "suspicious": "~/projects/gold-suspicious",
}

# OmniRoute free models
BASE = "http://localhost:20128/v1"
MK = ""

# OmniRoute client key (Hermes uses this for the router)
import re
from hurcules.routes import _default_key_file
try:
    j = json.load(open(_default_key_file()))
    MK = j.get("oss", {}).get("llm", {}).get("config", {}).get("api_key", "")
except OSError:
    pass
if not MK:
    print("ERROR: no OmniRoute key found"); sys.exit(1)

model = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
client = make_openai_client(BASE, MK, model)

repo_dir = os.path.expanduser(CLONES[GOLD_ID])
repo_map = map_repository(repo_dir)

print(f"[analyst] analyzing {GOLD_ID} ({repo_map['file_count']} files)...")
analysis = analyze(repo_map, client)
cands = analysis["capabilities"]
print(f"[analyst] {analysis['raw_candidate_count']} candidates, "
      f"validation_errors={len(analysis['validation_errors'])}")
for c in cands:
    print(f"  - {c['id']}: {c['name']} [{c['ontology_type']}] conf={c['confidence']} "
          f"ev={len(c['evidence'])}")

print("[devil's-advocate] attacking candidates...")
survivors = challenge(cands, repo_map, client)
print(f"[advocate] {len(cands)} -> {len(survivors)} survived")
for c in survivors:
    print(f"  SURVIVED: {c['id']} {c['name']} [{c['ontology_type']}] conf={c['confidence']}")

out = ROOT / "data" / "stage3-analysis" / f"{GOLD_ID}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({
    "gold_id": GOLD_ID, "model": model,
    "analyst": analysis, "survivors": survivors,
}, indent=2, sort_keys=True) + "\n")
print(f"wrote {out}")