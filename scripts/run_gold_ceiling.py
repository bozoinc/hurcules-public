#!/usr/bin/env python3
"""Gold-set extraction CEILING harness (deterministic, no LLM, no network).

Runs the ceiling scorer across every gold repo: gold capabilities from
data/gold/<id>.yaml, extracted capabilities from existing pipeline output
(stage4-packages/<id>.json preferred, stage3-analysis/<id>.json fallback).
Writes data/ceiling-report.json (per-repo + aggregate precision/recall/
unsupported-rate).

This is a harness over ALREADY-PRODUCED output — it never spawns a model call.

Usage: python3 scripts/run_gold_ceiling.py [case_id[,case_id...]]
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from hurcules.ceiling import ceiling_score, ceiling_score_semantic

GOLD_DIR = ROOT / "data" / "gold"
STAGE4 = ROOT / "data" / "stage4-packages"
STAGE3 = ROOT / "data" / "stage3-analysis"
OUT = ROOT / "data" / "ceiling-report.json"


def discover_cases() -> list[str]:
    """Gold case ids, ordered as listed in README-index.yaml."""
    idx = yaml.safe_load((GOLD_DIR / "README-index.yaml").read_text()) or {}
    cases = [r.get("case_id") for r in idx.get("repos", []) if r.get("case_id")]
    if cases:
        return cases
    return sorted(p.stem for p in GOLD_DIR.glob("*.yaml")
                  if p.stem != "README-index")


def load_gold_caps(gid: str) -> list[dict]:
    p = GOLD_DIR / f"{gid}.yaml"
    if not p.exists():
        return []
    d = list(yaml.safe_load_all(p.open()))[0] or {}
    return d.get("capabilities", []) or []


def load_extracted_caps(gid: str) -> tuple[list[dict], str | None]:
    """Return (caps, source) — stage4-packages preferred, stage3 fallback."""
    p4 = STAGE4 / f"{gid}.json"
    if p4.exists():
        d = json.loads(p4.read_text())
        if d.get("ok"):
            return (d.get("package", {}).get("capabilities", []) or []), \
                "stage4-packages"
    p3 = STAGE3 / f"{gid}.json"
    if p3.exists():
        d = json.loads(p3.read_text())
        survivors = d.get("survivors")
        if survivors is None:
            survivors = (d.get("analyst") or {}).get("capabilities", [])
        return (survivors or []), "stage3-analysis"
    return [], None


def main() -> int:
    only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
    cases = [c for c in discover_cases() if not only or c in only]

    rows, totals = [], {"extracted": 0, "gold": 0, "matched": 0,
                        "semantic_matched": 0, "unsupported": 0}
    skipped = []

    for gid in cases:
        gold_caps = load_gold_caps(gid)
        extracted, source = load_extracted_caps(gid)
        if source is None:
            skipped.append({"gold_id": gid, "reason": "no extraction output"})
            continue
        s = ceiling_score(extracted, gold_caps)
        semi = ceiling_score_semantic(extracted, gold_caps)
        rows.append({
            "gold_id": gid,
            "source": source,
            "extracted_count": s["extracted_count"],
            "gold_count": s["gold_count"],
            "matching_count": s["matching_count"],
            "precision": s["precision"],
            "recall": s["recall"],
            "unsupported_rate": s["unsupported_rate"],
            "semantic_match_count": semi["matching_count"],
            "semantic_precision": semi["precision"],
            "semantic_recall": semi["recall"],
            "matching_ids": s["matching_ids"],
            "missing_gold": s["missing_gold"],
            "extra": s["extra"],
        })
        totals["extracted"] += s["extracted_count"]
        totals["gold"] += s["gold_count"]
        totals["matched"] += s["matching_count"]
        totals["semantic_matched"] += semi["matching_count"]
        totals["unsupported"] += s["unsupported_count"]

    aggregate = {
        "extracted_total": totals["extracted"],
        "gold_total": totals["gold"],
        "matched_total": totals["matched"],
        "precision": round(totals["matched"] / totals["extracted"], 4)
        if totals["extracted"] else 0.0,
        "recall": round(totals["matched"] / totals["gold"], 4)
        if totals["gold"] else 0.0,
        "semantic_matched_total": totals["semantic_matched"],
        "semantic_precision": round(totals["semantic_matched"] / totals["extracted"], 4)
        if totals["extracted"] else 0.0,
        "semantic_recall": round(totals["semantic_matched"] / totals["gold"], 4)
        if totals["gold"] else 0.0,
        "unsupported_rate": round(totals["unsupported"] / totals["extracted"], 4)
        if totals["extracted"] else 0.0,
    }

    report = {
        "schema": "hurcules.ceiling-report",
        "kind": "gold-set-extraction-ceiling",
        "method": "normalized-name 1:1 match; valid evidence = non-empty list",
        "scored_cases": len(rows),
        "skipped_cases": skipped,
        "aggregate": aggregate,
        "cases": rows,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")

    print(f"=== GOLD-SET EXTRACTION CEILING (scored {len(rows)}, "
          f"skipped {len(skipped)}) ===")
    for r in sorted(rows, key=lambda x: x["gold_id"]):
        print(f"  {r['gold_id']:20s} {r['source']:16s} "
              f"match={r['matching_count']:3d}/{r['gold_count']:3d} "
              f"prec={r['precision']:.2f} rec={r['recall']:.2f} "
              f"semi_rec={r['semantic_recall']:.2f} "
              f"unsup={r['unsupported_rate']:.2f}")
    a = aggregate
    print(f"\naggregate: extracted={a['extracted_total']} matched={a['matched_total']} "
          f"gold={a['gold_total']} | precision={a['precision']:.4f} "
          f"recall={a['recall']:.4f} "
          f"semantic_recall={a['semantic_recall']:.4f} "
          f"unsupported_rate={a['unsupported_rate']:.4f}")
    print(f"report written: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())