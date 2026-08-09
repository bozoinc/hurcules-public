"""HURCULES Stage 9 — Composition & Spawning at scale (A8 full).

Turns a task into a capability GRAPH, then assembles a fleet of bounded
sub-agents — each composed from APPROVED registry capabilities (never
templates), each carrying full provenance (caps + commits), with explicit
handoff edges between agents (AGENT-MAP: edges are data contracts).

Hard rules (all enforced, all tested):
  - 9.2 composition only uses APPROVED registry capabilities
  - 9.3 every assembled agent carries provenance (which caps, which commits)
  - 9.4 handoffs form a valid DAG; every edge is a declared contract
  - 9.5 spawn requires human approval; no agent self-modifies policy

Design: deterministic, LLM-free assembly (pure graph construction over the
registry). Fleet spec schema `hurcules.fleet-spec-v1`.
"""

from __future__ import annotations

import hashlib
import json

COMPOSITION_VERSION = "1.0.0"
FLEET_SCHEMA = "hurcules.fleet-spec-v1"


# ---------------------------------------------------------------------------
# Graph patterns (AGENT-MAP 9.4) — named topologies for handoff layout
# ---------------------------------------------------------------------------
PATTERNS = ("sequence", "fanout", "pipeline")


def _validate_pattern(pattern: str) -> None:
    if pattern not in PATTERNS:
        raise ValueError(f"unknown handoff pattern {pattern!r}; use one of {PATTERNS}")


# ---------------------------------------------------------------------------
# Capability selection (shared scoring; approved-only)
# ---------------------------------------------------------------------------

def _flatten_approved(registry) -> list[dict]:
    """Approved capabilities flattened with entry + commit provenance."""
    flat = []
    for entry in registry.list(status="approved"):
        for cap in entry.get("capabilities", []):
            flat.append({
                **cap,
                "_entry_id": entry.get("entry_id"),
                "_pkg_id": entry.get("pkg_id"),
                "_commit_sha": entry.get("commit_sha", ""),
            })
    return flat


def _select_caps(flat, required: list[str], top_k: int = 3) -> list[dict]:
    """Deterministic relevance selection (mirrors adapter scoring)."""
    from hurcules.adapter import _score_capability
    required_set = set(required)
    scored = [(c, _score_capability(c, required_set)) for c in flat]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, s in scored if s > 0][:top_k]


# ---------------------------------------------------------------------------
# Fleet assembly
# ---------------------------------------------------------------------------

def compose_fleet(
    task: str,
    roles: list[dict],
    registry,
    *,
    pattern: str = "pipeline",
) -> dict:
    """Assemble a fleet of sub-agents from approved registry capabilities.

    roles: list of {
        "id": str,                    # unique role id, e.g. "research"
        "job": str,                   # one-line charter (AGENT-MAP: one job)
        "required_capabilities": [str,...],
        "input_from": [role_id,...] | None,   # handoff edges (default: chain)
    }

    Returns a fleet spec: agents with provenance + a validated handoff DAG.
    """
    _validate_pattern(pattern)
    flat = _flatten_approved(registry)
    if not flat:
        return {"ok": False, "schema": FLEET_SCHEMA, "task": task,
                "reason": "no approved capabilities — nothing can spawn (D4)"}

    agents = []
    for role in roles:
        role_id = role.get("id")
        caps = _select_caps(flat, role.get("required_capabilities", []))
        if not caps:
            return {"ok": False, "schema": FLEET_SCHEMA, "task": task,
                    "reason": f"no approved capability matched role {role_id!r}",
                    "role": role_id}
        agents.append({
            "agent_id": f"{role_id}-{hashlib.sha1(role_id.encode()).hexdigest()[:6]}",
            "role": role_id,
            "job": role.get("job", ""),
            "composed_from": [
                {
                    "capability_id": c.get("id"),
                    "name": c.get("name"),
                    "ontology_type": c.get("ontology_type"),
                    "confidence": c.get("confidence"),
                    "registry_entry": c.get("_entry_id"),
                    "pkg": c.get("_pkg_id"),
                    "commit_sha": c.get("_commit_sha", ""),
                }
                for c in caps
            ],
        })

    # 9.4 handoff DAG: explicit edges; default = input_from chain, else linear
    edges = _build_edges(agents, roles)
    cycles = _find_cycle(agents, edges)
    if cycles:
        return {"ok": False, "schema": FLEET_SCHEMA, "task": task,
                "reason": f"handoff graph contains a cycle: {cycles}"}

    return {
        "ok": True,
        "schema": FLEET_SCHEMA,
        "composition_version": COMPOSITION_VERSION,
        "task": task,
        "pattern": pattern,
        "agents": agents,
        "handoffs": edges,
        "approval_required": True,      # 9.5: no spawn without human approval
        "self_modify_policy": "DENIED", # 9.5: agents never change their own spec
        "status": "pending_approval",
    }


def _build_edges(agents: list[dict], roles: list[dict]) -> list[dict]:
    """Edge list: {from_agent, to_agent, contract} — DAG edges only."""
    id_to_agent = {a["role"]: a["agent_id"] for a in agents}
    role_meta = {r["id"]: r for r in roles}

    edges = []
    for r in roles:
        to = id_to_agent.get(r["id"])
        if not to:
            continue
        srcs = r.get("input_from")
        if srcs is None:  # default: previous role in declared order
            idx = [x["id"] for x in roles].index(r["id"])
            if idx > 0:
                srcs = [roles[idx - 1]["id"]]
        for s in (srcs or []):
            frm = id_to_agent.get(s)
            if frm:
                edges.append({
                    "from_agent": frm,
                    "to_agent": to,
                    "contract": f"{s}->{r['id']}",
                })
    return edges


def _find_cycle(agents: list[dict], edges: list[dict]) -> list[str] | None:
    """DFS cycle detection over the handoff DAG; returns cycle path or None."""
    adj = {a["agent_id"]: [] for a in agents}
    for e in edges:
        adj.setdefault(e["from_agent"], []).append(e["to_agent"])
    WHITE, GREY, BLACK = 0, 1, 2
    color = {a["agent_id"]: WHITE for a in agents}
    stack: list[str] = []

    def dfs(u: str) -> list[str] | None:
        color[u] = GREY
        stack.append(u)
        for v in adj.get(u, []):
            if color[v] == GREY:
                return stack[stack.index(v):] + [v]
            if color[v] == WHITE:
                cyc = dfs(v)
                if cyc:
                    return cyc
        stack.pop()
        color[u] = BLACK
        return None

    for a in agents:
        if color[a["agent_id"]] == WHITE:
            cyc = dfs(a["agent_id"])
            if cyc:
                return cyc
    return None


def fleet_digest(fleet: dict) -> str:
    """Deterministic digest of a fleet spec (provenance-graph fingerprint)."""
    payload = {
        "task": fleet.get("task") or "",
        "agents": [(a.get("agent_id") or "", [c.get("capability_id", "") for c in a.get("composed_from", [])])
                   for a in fleet.get("agents", [])],
        "handoffs": sorted((e.get("from_agent", ""), e.get("to_agent", ""))
                           for e in fleet.get("handoffs", [])),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
