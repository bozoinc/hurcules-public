"""HURCULES Stage 6 — Hermes Adapter / Spawner (A8).

Given a task + required capabilities, select APPROVED registry capabilities and
compose a bounded sub-agent definition. Composes from capabilities (6.3), never
copy-pastes prompt templates. No spawn happens here — this produces the agent
SPEC that must pass the four-part approval (D4) before any spawn.

Public seam: compose_agent(task, required_capabilities, registry, top_k) -> dict
"""
from __future__ import annotations

ADAPTER_VERSION = "1.0.0"


def can_execute(spec: dict, *, approved: bool, sandbox_available: bool) -> dict:
    """Opt-in execution gate (Stage 7, D3/D4).

    Execution of a composed agent is NEVER the default. It requires BOTH:
      1. the composing capabilities were human-approved (D4), AND
      2. a real sandbox boundary is present (Stage 7 — system property,
         not a system-prompt promise).
    Returns a decision dict: {'execute': bool, 'reason': str, 'method': str}.
    """
    if not spec.get("ok"):
        return {"execute": False, "reason": "spec invalid", "method": "none"}
    if not approved:
        return {"execute": False, "reason": "capabilities not human-approved (D4)",
                "method": "none"}
    if not sandbox_available:
        return {"execute": False, "reason": "no real sandbox boundary available (Stage 7)",
                "method": "none"}
    return {"execute": True, "reason": "approved + sandboxed", "method": "docker-sandbox"}


# Back-compat alias used by tests/scripts
execution_gate = can_execute


def _score_capability(cap: dict, required: set[str]) -> float:
    """Naive capability-task relevance: name/ontology overlap with requirements."""
    name = (cap.get("name") or "").lower()
    ot = (cap.get("ontology_type") or "").lower()
    score = 0.0
    for req in required:
        r = req.lower()
        if r in name or name in r:
            score += 1.0
        elif any(w in name for w in r.split()):
            score += 0.5
    if ot in required or any(r in ot for r in required):
        score += 0.3
    return score


def compose_agent(task: str, required_capabilities: list[str],
                  registry, top_k: int = 5) -> dict:
    """Select approved capabilities matching required_capabilities.

    registry: object with list(status='approved') -> [entries with
    'capabilities': [{id,name,ontology_type,confidence}]]
    """
    approved_entries = registry.list(status="approved")
    if not approved_entries:
        return {
            "ok": False,
            "reason": "no approved capabilities in registry — nothing can spawn (D4)",
            "task": task,
            "composed": None,
        }

    # flatten approved capabilities with their entry provenance
    flat = []
    for entry in approved_entries:
        for cap in entry.get("capabilities", []):
            flat.append({**cap, "_entry_id": entry.get("entry_id"),
                         "_pkg_id": entry.get("pkg_id")})

    required = set(required_capabilities)
    scored = [(c, _score_capability(c, required)) for c in flat]
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = [c for c, s in scored if s > 0][:top_k]

    if not selected:
        return {
            "ok": False,
            "reason": f"no approved capability matched requirements {sorted(required)}",
            "task": task,
            "composed": None,
        }

    agent_spec = {
        "ok": True,
        "schema": "hurcules.agent-spec-v1",
        "adapter_version": ADAPTER_VERSION,
        "task": task,
        "required_capabilities": sorted(required),
        "composed_from": [
            {
                "capability_id": c.get("id"),
                "name": c.get("name"),
                "ontology_type": c.get("ontology_type"),
                "confidence": c.get("confidence"),
                "registry_entry": c.get("_entry_id"),
                "pkg": c.get("_pkg_id"),
            }
            for c in selected
        ],
        "approval_required": True,  # D4: never spawn without human approval
        "status": "pending_approval",
    }
    return agent_spec