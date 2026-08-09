#!/usr/bin/env python3
"""Stage 5 evaluation harness — full suite across all gold repos.

For each repo: deterministic checks (citation, schema, unsupported-rate via
evaluator.py) + semantic gold-match gate (reuses judged matches) + reproducibility
(same repo mapped twice -> identical). Produces data/stage5-eval/<gid>.json and
an aggregate report.

Usage: python3 scripts/run_stage5_eval.py
"""
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from hurcules.evaluator import evaluate_capabilities
from hurcules.mapper import map_repository

GOLD_DIR = ROOT / "data" / "gold"
CONSOLIDATED_DIR = ROOT / "data" / "consolidated"
STAGE2 = ROOT / "data" / "stage2-baseline"
OUT = ROOT / "data" / "stage5-eval"
OUT.mkdir(parents=True, exist_ok=True)

CLONE_MAP = {
    "archon": "~/projects/Archon", "mem0": "~/projects/mem0",
    "jq": "~/projects/gold-jq", "ripgrep": "~/projects/gold-ripgrep",
    "express": "~/projects/gold-express", "click": "~/projects/gold-click",
    "fd": "~/projects/gold-fd", "pytest": "~/projects/gold-pytest",
    "prettier": "~/projects/gold-prettier", "zx": "~/projects/gold-zx",
    "yq": "~/projects/gold-yq", "bat": "~/projects/gold-bat",
    "tokei": "~/projects/gold-tokei",
    "mattpocock-skills": "~/projects/gold-mattpocock-skills",
    "awesome-graph-eng": "~/projects/gold-awesome-graph-eng",
    "nolicense": "~/projects/gold-nolicense",
    "suspicious": "~/projects/gold-suspicious",
    "hexyl": "~/projects/gold-hexyl", "ratty": "~/projects/gold-ratty",
    "navi": "~/projects/gold-navi", "claimgap": "~/projects/gold-claimgap5",
}

# gold-capability name -> judged matches live in data/consolidated/<gid>.judged.json
def gold_names(gid):
    p = GOLD_DIR / f"{gid}.yaml"
    if not p.exists():
        try:
            idx = yaml.safe_load(open(GOLD_DIR / "README-index.yaml"))
            for r in idx.get("repos", []):
                if r.get("case_id") == gid:
                    p = GOLD_DIR / Path(r["file"]).name
                    break
        except Exception:
            return []
    try:
        d = list(yaml.safe_load_all(open(p)))[0]
    except Exception:
        return []
    return [c.get("name", "") for c in d.get("capabilities", [])]


def judged_matches(gid):
    p = CONSOLIDATED_DIR / f"{gid}.judged.json"
    if not p.exists():
        return None
    return json.load(open(p)).get("matches", [])


def main():
    rows = []
    ts_up = ts_n = 0  # unsupported-rate aggregate
    ts_gold = ts_goldmatch = 0  # gold-match aggregate
    ts_sem = 0
    for gid in sorted(CLONE_MAP):
        cons = CONSOLIDATED_DIR / f"{gid}.json"
        s2 = STAGE2 / f"{gid}.json"
        if not cons.exists() or not s2.exists():
            print(f"[skip] {gid}: missing consolidated/stage2")
            continue
        caps = json.load(open(cons))
        repo_map = json.load(open(s2))
        tree = repo_map.get("file_tree", [])

        # 1. deterministic gates
        evalr = evaluate_capabilities(caps, tree)
        unsupported = evalr["unsupported_capability_rate"]
        ts_up += evalr["unsupported_capability_count"]
        ts_n += evalr["capability_count"]

        # 2. semantic gold-match gate (from judged cache)
        gold = gold_names(gid)
        matches = judged_matches(gid)
        matched = sum(1 for m in (matches or []) if m.get("matched"))
        goldmatch_rate = matched / len(gold) if gold else 0.0
        ts_gold += len(gold); ts_goldmatch += matched

        # 3. reproducibility: map twice, compare (cheap: deterministic)
        clone = os.path.expanduser(CLONE_MAP[gid])
        try:
            m1 = map_repository(clone)
            m2 = map_repository(clone)
            reproducible = json.dumps(m1, sort_keys=True) == json.dumps(m2, sort_keys=True)
        except Exception:
            reproducible = None  # clone may be missing in eval-only context

        status = "PASS" if unsupported < 0.05 else "REVIEW"
        rows.append((gid, evalr["capability_count"], unsupported,
                     goldmatch_rate, matched, len(gold), reproducible, status))

        out = OUT / f"{gid}.json"
        out.write_text(json.dumps({
            "gold_id": gid,
            "capability_count": evalr["capability_count"],
            "unsupported_capability_rate": unsupported,
            "gold_match_rate": goldmatch_rate,
            "gold_matched": matched, "gold_total": len(gold),
            "reproducible": reproducible,
            "status": status,
            "verdicts": evalr["verdicts"],
        }, indent=2, sort_keys=True) + "\n")

    # aggregate
    agg_unsupported = ts_up / ts_n if ts_n else 0.0
    agg_goldmatch = ts_goldmatch / ts_gold if ts_gold else 0.0
    print("=== STAGE 5 EVALUATION (gold set) ===")
    for gid, n, up, gm, m, g, rep, st in rows:
        print(f"  {gid:20s} caps={n:2d} unsupported={up:0.2f} goldmatch={gm:0.2f} "
              f"({m}/{g}) reproducible={rep} [{st}]")
    print(f"\naggregate: unsupported_rate={agg_unsupported:0.4f} "
          f"gold_match_rate={agg_goldmatch:0.3f}")
    print(f"records written to {OUT}/")


if __name__ == "__main__":
    main()