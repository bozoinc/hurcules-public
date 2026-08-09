"""TDD tests for Stage 6 Hermes adapter (compose from approved capabilities)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.registry import Registry
from hurcules.adapter import compose_agent

PKG = {
    "provenance": {"repository": "owner/repo"},
    "capabilities": [
        {"id": "c1", "name": "JSON processing", "ontology_type": "TOOL", "confidence": 0.9},
        {"id": "c2", "name": "Workflow runner", "ontology_type": "WORKFLOW", "confidence": 0.85},
        {"id": "c3", "name": "Web search", "ontology_type": "TOOL", "confidence": 0.8},
    ],
}


def _approved_registry(tmpdir):
    r = Registry(os.path.join(tmpdir, "reg.json"))
    e = r.register(PKG)
    r.approve(e["entry_id"], "owner")
    return r


def test_no_approved_capabilities_blocks_spawn():
    with tempfile.TemporaryDirectory() as td:
        r = Registry(os.path.join(td, "reg.json"))
        r.register(PKG)  # candidate only, never approved
        spec = compose_agent("do json stuff", ["json"], r)
        assert spec["ok"] is False
        assert "no approved capabilities" in spec["reason"]


def test_composes_from_approved_only():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        spec = compose_agent("process json", ["json"], r)
        assert spec["ok"] is True
        assert spec["approval_required"] is True
        assert spec["status"] == "pending_approval"
        names = [c["name"] for c in spec["composed_from"]]
        assert any("JSON" in n for n in names)
        assert all(c["registry_entry"] for c in spec["composed_from"])


def test_no_match_blocks():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        spec = compose_agent("fly a rocket", ["rocket"], r)
        assert spec["ok"] is False
        assert "no approved capability matched" in spec["reason"]


def test_spec_traces_provenance():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        spec = compose_agent("web search task", ["search"], r)
        c = spec["composed_from"][0]
        assert c["pkg"] == "owner/repo"
        assert c["ontology_type"] in {"TOOL", "WORKFLOW"}


def test_compose_is_deterministic():
    with tempfile.TemporaryDirectory() as td:
        r = _approved_registry(td)
        a = compose_agent("process json", ["json"], r)
        b = compose_agent("process json", ["json"], r)
        assert a == b