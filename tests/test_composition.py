"""TDD tests for Stage 9 composition & spawning (fleet assembly)."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.registry import Registry
from hurcules.composition import (
    PATTERNS,
    _find_cycle,
    _validate_pattern,
    compose_fleet,
    fleet_digest,
)

PKG = {
    "provenance": {"repository": "owner/repo", "commit_sha": "abc123"},
    "capabilities": [
        {"id": "c1", "name": "Market research", "ontology_type": "TOOL", "confidence": 0.9},
        {"id": "c2", "name": "Workflow executor", "ontology_type": "WORKFLOW", "confidence": 0.85},
        {"id": "c3", "name": "Report writer", "ontology_type": "TOOL", "confidence": 0.8},
    ],
}

ROLES = [
    {"id": "research", "job": "gather market facts",
     "required_capabilities": ["market"]},
    {"id": "analyze", "job": "synthesize strategy",
     "required_capabilities": ["workflow"]},
    {"id": "report", "job": "write dossier",
     "required_capabilities": ["report"]},
]


def _approved_registry(tmpdir):
    r = Registry(os.path.join(tmpdir, "reg.json"))
    e = r.register(PKG)
    r.approve(e["entry_id"], "owner")
    return r


def test_patterns_valid():
    assert PATTERNS == ("sequence", "fanout", "pipeline")
    try:
        _validate_pattern("bogus")
        assert False
    except ValueError:
        pass


def test_compose_needs_approved():
    with tempfile.TemporaryDirectory() as td:
        r = Registry(os.path.join(td, "reg.json"))
        r.register(PKG)  # candidate only
        fleet = compose_fleet("do all", ROLES, r)
        assert fleet["ok"] is False
        assert "no approved capabilities" in fleet["reason"]


def test_compose_requires_approval_flag():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        fleet = compose_fleet("task", ROLES, r)
        assert fleet["approval_required"] is True
        assert fleet["self_modify_policy"] == "DENIED"
        assert fleet["status"] == "pending_approval"


def test_compose_multi_agent_fleet():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        fleet = compose_fleet("build strategy", ROLES, r)
        assert fleet["ok"] is True
        assert len(fleet["agents"]) == 3
        roles = {a["role"] for a in fleet["agents"]}
        assert roles == {"research", "analyze", "report"}


def test_every_agent_has_provenance():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        fleet = compose_fleet("task", ROLES, r)
        for agent in fleet["agents"]:
            for cap in agent["composed_from"]:
                assert cap["registry_entry"]
                assert cap["commit_sha"] == "abc123"
                assert cap["pkg"] == "owner/repo"


def test_handoffs_form_chain_without_cycle():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        fleet = compose_fleet("task", ROLES, r)
        # default: linear chain research->analyze->report
        ids = [a["agent_id"] for a in fleet["agents"]]
        froms = [e["from_agent"] for e in fleet["handoffs"]]
        tos = [e["to_agent"] for e in fleet["handoffs"]]
        assert len(fleet["handoffs"]) == 2
        assert (ids[0], ids[1]) == (froms[0], tos[0])
        assert (ids[1], ids[2]) == (froms[1], tos[1])


def test_explicit_handoffs_respected():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        roles = [
            {"id": "a", "job": "a", "required_capabilities": ["market"],
             "input_from": []},
            {"id": "b", "job": "b", "required_capabilities": ["report"],
             "input_from": ["a"]},
        ]
        fleet = compose_fleet("t", roles, r)
        assert len(fleet["handoffs"]) == 1
        assert fleet["handoffs"][0]["contract"] == "a->b"


def test_cycle_detected_and_rejected():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        roles = [
            {"id": "a", "job": "a", "required_capabilities": ["market"],
             "input_from": ["b"]},
            {"id": "b", "job": "b", "required_capabilities": ["report"],
             "input_from": ["a"]},
        ]
        fleet = compose_fleet("t", roles, r)
        assert fleet["ok"] is False
        assert "cycle" in fleet["reason"]


def test_capabilities_only_approved():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        # try a role with a capability that is NOT in the registry at all
        roles = [{"id": "x", "job": "x", "required_capabilities": ["nonsense"]}]
        fleet = compose_fleet("t", roles, r)
        assert fleet["ok"] is False
        assert "no approved capability matched" in fleet["reason"]


def test_fleet_digest_deterministic():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        a = compose_fleet("task", ROLES, r)
        b = compose_fleet("task", ROLES, r)
        assert fleet_digest(a) == fleet_digest(b)
        assert len(fleet_digest(a)) == 16


def test_graph_topology_dag_is_acyclic():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        fleet = compose_fleet("task", ROLES, r)
        assert _find_cycle(fleet["agents"], fleet["handoffs"]) is None