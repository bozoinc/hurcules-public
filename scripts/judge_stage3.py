#!/usr/bin/env python3
"""Semantic judge: score Stage 3 survivors vs gold capabilities using an LLM.

The naive name-overlap scorer undercounts because analyst and gold use different
phrasing for the same capability. This judge asks a free LLM to match gold
capabilities to analyst survivors (semantic equivalence), then reports
precision / recall properly.

Usage: python3 scripts/judge_stage3.py [id1,id2,...]
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from hurcules.analyst import make_openai_client

import yaml

GOLD_DIR = ROOT / "data" / "gold"
ANALYSIS_DIR = ROOT / "data" / "stage3-analysis"
BASE = "http://localhost:20128/v1"
MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"


def get_key():
    from hurcules.routes import _default_key_file
    j = json.load(open(_default_key_file()))
    return j["oss"]["llm"]["config"]["api_key"]


def load_gold_caps(gid: str) -> list[dict]:
    """Return full gold capability objects (name + evidence)."""
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
    if not p.exists():
        return []
    try:
        d = list(yaml.safe_load_all(open(p)))[0]
    except Exception:
        return []
    return d.get("capabilities", [])


def judge(client, gid, gold_names, surv_names, gold_full=None, surv_full=None):
    if not surv_names or not gold_names:
        return [], "no names to compare"
    # Compare full capability objects when available (name + evidence + ontology),
    # falling back to names. This allows fair semantic equivalence judgement.
    gold_view = gold_full if gold_full else gold_names
    surv_view = surv_full if surv_full else surv_names
    prompt = (
        "You are an evaluation judge. The GOLD capabilities of a repository are "
        "the ground truth. The ANALYST produced candidate capabilities with "
        "wording that may differ. For EACH gold capability, decide if the "
        "analyst surfaced an EQUIVALENT capability — same functionality, same "
        "purpose — even if the name differs. Equivalent capability in different "
        "words COUNTS as matched. Use the evidence/scope to judge functional "
        "equivalence, not just string similarity. Return JSON:\n"
        '{"matches": [{"gold": "<gold index/name>", "matched": true, '
        '"analyst": "<survivor name or null>"}]}\n'
        f"GOLD:\n{json.dumps(gold_view, indent=1, ensure_ascii=False)}\n"
        f"ANALYST:\n{json.dumps(surv_view, indent=1, ensure_ascii=False)}\n"
        "Be fair: a real capability in different words = matched."
    )
    messages = [
        {"role": "system", "content": "You are a rigorous but fair evaluation judge. Respond only with the JSON."},
        {"role": "user", "content": prompt},
    ]
    last_err = None
    for attempt in range(3):
        try:
            raw = client(messages)
            start, end = raw.find("{"), raw.rfind("}")
            parsed = json.loads(raw[start:end + 1])
            return parsed.get("matches", []), None
        except Exception as e:
            last_err = e
            import time
            time.sleep(5 * (attempt + 1))
    return [], f"judge failed after 3 retries: {last_err}"


def main():
    only = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
    # mode: 'consolidated' uses data/consolidated/<id>.json as the survivor source
    mode = "consolidated" if os.environ.get("JUDGE_SOURCE") == "consolidated" else "stage3"
    source_dir = ROOT / "data" / "consolidated" if mode == "consolidated" else ANALYSIS_DIR
    client = make_openai_client(BASE, get_key(), MODEL)
    rows = []
    ts = tm = tg = 0
    for f in sorted(source_dir.glob("*.json")):
        gid = f.stem
        if only and gid not in only:
            continue
        try:
            data = json.load(open(f))
        except Exception:
            continue
        surv_full = data if isinstance(data, list) else data.get("survivors", [])
        surv = [c.get("name", "") for c in surv_full]
        gold_full = load_gold_caps(gid)
        gold = [c.get("name", "") for c in gold_full]
        out_file = source_dir / f"{gid}.judged.json"
        if out_file.exists():
            j = json.load(open(out_file))
            matches = j.get("matches", [])
            print(f"  {gid:20s} (cached) matched={sum(1 for m in matches if m.get('matched')):2d}/{len(gold):2d}")
        else:
            matches, err = judge(client, gid, gold, surv, gold_full, surv_full)
            if err:
                print(f"[skip] {gid}: {err}")
                continue
            out_file.write_text(json.dumps({"gold_id": gid, "matches": matches},
                                           indent=2, sort_keys=True) + "\n")
        matched = sum(1 for m in matches if m.get("matched"))
        ts += len(surv); tm += matched; tg += len(gold)
        p = matched / len(surv) if surv else 0.0
        r = matched / len(gold) if gold else 0.0
        rows.append((gid, len(surv), matched, len(gold), p, r))
        print(f"  {gid:20s} surv={len(surv):3d} matched={matched:2d}/{len(gold):2d} "
              f"precision={p:0.2f} recall={r:0.2f}")

    print(f"\naggregate: survivors={ts} matched={tm} gold={tg} "
          f"precision={tm/ts if ts else 0:0.3f} recall={tm/tg if tg else 0:0.3f}")


if __name__ == "__main__":
    main()