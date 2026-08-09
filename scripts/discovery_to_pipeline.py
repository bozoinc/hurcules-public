#!/usr/bin/env python3
"""Stage 8.3 — feed a discovered repo through the SAME ingestion pipeline.

Discovery finds candidates (8.1/8.2); this script hands each chosen repo to the
identical map->analyst->advocate->compiler chain used for the gold set (no
shortcuts), writing data/stage4-packages/<id>.json when it compiles.

Usage:
  python3 scripts/discovery_to_pipeline.py [--query "..."] [--limit N] [--clone-dir DIR]
  python3 scripts/discovery_to_pipeline.py --repo owner/name    # ingest a specific candidate

Cost limits: shallow clone, pinned commit, per_page cap, no private repos.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from hurcules.discovery import gh_search, top
from hurcules.mapper import map_repository
from hurcules.analyst import analyze
from hurcules.devils_advocate import challenge
from hurcules.compiler import compile_package
from hurcules.ledger import RunReport, attach_usage
from hurcules.routes import Router

DEFAULT_BASE = "http://127.0.0.1:20128/v1"   # OmniRoute proxy (cloud free routes)
MODEL_LIST = "openrouter/nvidia/nemotron-3-super-120b-a12b:free," \
             "openrouter/nemotron-super/ultra:free,oc/deepseek-v4-flash-free"

BASE = os.environ.get("HURCULES_BASE", DEFAULT_BASE)
MODEL = os.environ.get("HURCULES_MODEL", MODEL_LIST.split(",")[0])


def get_key():
    # poll the configured key if present; a local OmniRoute proxy needs none
    import json as _json
    from hurcules.routes import _default_key_file
    try:
        j = _json.load(open(_default_key_file()))
        return j["oss"]["llm"]["config"]["api_key"]
    except Exception:
        return ""


def _clone(repo: str, dest: Path) -> bool:
    proc = subprocess.run(
        ["git", "clone", "--depth", "1",
         f"https://github.com/{repo}.git", str(dest)],
        capture_output=True, text=True, timeout=120,
    )
    return proc.returncode == 0


def ingest(repo: str, out_dir: Path, clone_root: Path) -> dict:
    """Clone then run the full ingestion chain for ONE repo (SAME as gold)."""
    clone_dir = clone_root / repo.replace("/", "__")
    rpt = RunReport(repo=repo)
    router = Router.from_env()
    router.probe()
    if not _clone(repo, clone_dir):
        return {"repo": repo, "ok": False, "stage": "clone", "error": "clone failed"}
    try:
        with rpt.stage("map"):
            repo_map = map_repository(str(clone_dir))
        client = attach_usage(router.client_for("analyst"), MODEL, BASE)
        with rpt.stage("analyst", client):
            analysis = analyze(repo_map, client)
        if analysis.get("conclusion") == "inconclusive":
            # Quality floor (W1-[1]): never a silent valid empty package.
            rpt.save(ROOT / "data" / "run-reports")
            return {"repo": repo, "ok": False, "stage": "analyst",
                    "error": "inconclusive extraction (empty/unparseable) "
                             "— not a valid empty package",
                    "conclusion": "inconclusive"}
        with rpt.stage("advocate", client):
            survivors = challenge(analysis["capabilities"], repo_map, client)
        with rpt.stage("compile"):
            result = compile_package({"capabilities": survivors,
                                      "conclusion": analysis.get("conclusion", "ok")},
                                     repo_map, str(clone_dir))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{repo.replace('/', '__')}.json").write_text(
            json.dumps({"repo": repo, **result}, indent=2))
        rpt.save(ROOT / "data" / "run-reports")
        return {"repo": repo, "ok": bool(result.get("ok")),
                "mapped_files": repo_map.get("file_count"),
                "caps": len(result.get("package", {}).get("capabilities", [])) if result.get("ok") else len(result.get("errors", []))}
    except Exception as e:  # hostile-by-default: never crash the sweep
        rpt.save(ROOT / "data" / "run-reports")
        return {"repo": repo, "ok": False, "stage": "ingest", "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="topic:agent language:python")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--repo", default="", help="ingest a single known repo instead")
    ap.add_argument("--clones", default="/tmp/hurcules-discovery", help="clone root dir")
    args = ap.parse_args()

    out_dir = ROOT / "data" / "stage4-packages"
    clone_root = Path(args.clones)
    clone_root.mkdir(parents=True, exist_ok=True)

    if args.repo:
        repos = [args.repo]
    else:
        found = gh_search(args.query, limit=args.limit)
        repos = [c.repo for c in top(found, args.limit)]
        print(f"discovered {len(repos)} candidate(s): {repos}")

    reports = [ingest(r, out_dir, clone_root) for r in repos]
    for rep in reports:
        status = "OK" if rep.get("ok") else "FAIL"
        print(f"[{status}] {rep['repo']}  mapped={rep.get('mapped_files')}")
    return 0 if all(r.get("ok") for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())