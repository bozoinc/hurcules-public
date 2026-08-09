#!/usr/bin/env python3
"""Score Stage 3 analyst survivors against gold capabilities.

Compares data/stage3-analysis/<id>.json (survivors) with data/gold/<id>.yaml
(gold capabilities) by normalized-name Jaccard overlap. Reports per-repo and
aggregate capability PRECISION (survivors matched / survivors) and RECALL
(survivors matched / gold capabilities).
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
GOLD_DIR = ROOT / "data" / "gold"
ANALYSIS_DIR = ROOT / "data" / "stage3-analysis"

STOP = {"a", "an", "the", "and", "or", "of", "for", "to", "in", "with", "on",
        "using", "at", "is"}


def norm(name: str) -> set[str]:
    import re
    parts = re.split(r"[^a-z0-9]+", str(name).lower())
    return {p for p in parts if p and p not in STOP}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_gold(gold_id: str) -> list[str]:
    p = GOLD_DIR / f"{gold_id}.yaml"
    if not p.exists():
        try:
            idx = yaml.safe_load(open(GOLD_DIR / "README-index.yaml"))
            for r in idx.get("repos", []):
                if r.get("case_id") == gold_id:
                    p = GOLD_DIR / Path(r["file"]).name
                    break
        except Exception:
            return []
    if not p.exists():
        return []
    try:
        d = list(yaml.safe_load_all(open(p)))[0]
    except Exception:
        return []
    return [c.get("name", "") for c in d.get("capabilities", [])]


def main():
    only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
    total_surv = total_match = total_gold = 0
    rows = []
    for f in sorted(ANALYSIS_DIR.glob("*.json")):
        gid = f.stem
        if only and gid not in only:
            continue
        try:
            data = json.load(open(f))
        except Exception:
            continue
        survivors = data.get("survivors", [])
        gold_names = load_gold(gid)
        gold_tokens = [norm(g) for g in gold_names]
        surv_names = [c.get("name", "") for c in survivors]
        surv_tokens = [norm(s) for s in surv_names]

        # for each survivor, is it a genuine input capability (precision)?
        matched = 0
        for st in surv_tokens:
            if any(jaccard(st, gt) >= 0.5 for gt in gold_tokens):
                matched += 1
        # recall: of gold caps, how many did we surface?
        recalled = 0
        for gt in gold_tokens:
            if any(jaccard(st, gt) >= 0.5 for st in surv_tokens):
                recalled += 1

        total_surv += len(survivors)
        total_match += matched
        total_gold += len(gold_names)
        p = matched / len(survivors) if survivors else 0.0
        r = recalled / len(gold_names) if gold_names else 0.0
        rows.append((gid, len(survivors), matched, len(gold_names), p, r))

    print("=== STAGE 3 vs GOLD (name-overlap) ===")
    for gid, surv, m, gold, p, r in rows:
        print(f"  {gid:20s} surv={surv:3d} matched={m:3d}/{gold:3d} "
              f"precision={p:0.2f} recall={r:0.2f}")
    print(f"\naggregate: survivors={total_surv} matched={total_match} "
          f"gold={total_gold} precision={total_match/total_surv if total_surv else 0:0.3f} "
          f"recall={total_match/total_gold if total_gold else 0:0.3f}")


if __name__ == "__main__":
    main()