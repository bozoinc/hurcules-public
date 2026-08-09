#!/usr/bin/env python3
"""Chain Stage 2-3-4 for a gold repo: map -> analyst -> advocate -> compiler.

Usage: python3 scripts/pipeline.py <gold_id>
Writes data/stage4-packages/<gold_id>.json (validated package or error report).
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
from hurcules.compiler import compile_package

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

BASE = "http://localhost:20128/v1"
MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"


def get_key():
    from hurcules.routes import _default_key_file
    j = json.load(open(_default_key_file()))
    return j["oss"]["llm"]["config"]["api_key"]


def main():
    repo_dir = os.path.expanduser(CLONES[GOLD_ID])
    if not os.path.isdir(repo_dir):
        print(f"ERROR: no clone {repo_dir}"); sys.exit(1)

    print(f"[map] {GOLD_ID}")
    repo_map = map_repository(repo_dir)

    client = make_openai_client(BASE, get_key(), MODEL)
    print("[analyst]")
    analysis = analyze(repo_map, client)
    cands = analysis["capabilities"]
    print(f"  {len(cands)} candidates")
    print("[advocate]")
    survivors = challenge(cands, repo_map, client)
    print(f"  {len(survivors)} survivors")

    print("[compiler]")
    result = compile_package({"capabilities": survivors}, repo_map, repo_dir)
    if result["ok"]:
        print(f"  PACKAGE OK: {len(result['package']['capabilities'])} capabilities")
    else:
        print(f"  REJECTED: {len(result['errors'])} errors")

    OUT = ROOT / "data" / "stage4-packages"
    OUT.mkdir(parents=True, exist_ok=True)
    outfile = OUT / f"{GOLD_ID}.json"
    outfile.write_text(json.dumps({"gold_id": GOLD_ID, **result}, indent=2, sort_keys=True) + "\n")
    print(f"  wrote {outfile}")


if __name__ == "__main__":
    main()