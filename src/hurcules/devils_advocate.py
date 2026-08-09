"""HURCULES Stage 3 — Devil's Advocate (A2a, QIR Annealing).

Adversarial verification pass. A second LLM attacks each capability candidate:
"is this really in the code, or is the README lying / is this fabricated?"
Only candidates that SURVIVE are returned. Prevents README-marketing being
mistaken for implemented behavior and fabricated capabilities shipping.

Public seam: challenge(candidates, repo_map, client) -> list[dict]
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

ADVOCATE_VERSION = "1.0.0"

ADVOCATE_PROMPT = (
    "You are a skeptical code reviewer (devil's advocate). A capability analyst "
    "produced these capability candidates for a repository. Your job is to "
    "ATTACK each one: look for capabilities that are README marketing not "
    "implemented code, fabricated evidence, or overclaimed confidence.\n"
    "IMPORTANT: be CONSERVATIVE — only mark survives=false when you are HIGHLY "
    "CONFIDENT the capability is fabricated or purely marketing with no code "
    "backing. If in doubt, or if the candidate has plausible evidence files "
    "listed, mark survives=true. Your job is to catch fabrication, not to "
    "under-report legitimate capabilities. When a candidate is killed, give a "
    "precise reason citing the specific fabrication.\n"
    "For EACH candidate reply with a verdict JSON:\n"
    '{"verdicts": [{"id": "c1", "survives": true, "reason": "..."}, '
    '{"id": "c2", "survives": false, "reason": "..."}]}\n'
    "Default to survives=true unless you're confident of fabrication."
)


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON in advocate output")
    return json.loads(text[start:end + 1])


def challenge(candidates: list[dict], repo_map: dict,
              client: Callable[[list[dict]], str]) -> list[dict]:
    if not candidates:
        return []
    user = (
        "Capability candidates:\n"
        f"{json.dumps({'capabilities': candidates}, indent=2, sort_keys=True)}\n"
        "Evidence is limited to these repo paths (do not invent others):\n"
        f"{json.dumps(repo_map.get('file_tree', []), indent=0)}\n"
        "Attack each candidate. Return only the verdicts JSON."
    )
    raw = client([
        {"role": "system", "content": ADVOCATE_PROMPT},
        {"role": "user", "content": user},
    ])
    parsed = _extract_json(raw)
    verdicts = parsed.get("verdicts", []) if isinstance(parsed, dict) else []
    kill_ids = {v.get("id") for v in verdicts if not v.get("survives")
                and v.get("id")}
    survivors = [c for c in candidates if c["id"] not in kill_ids]
    return survivors