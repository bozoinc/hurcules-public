"""TDD tests for Stage 6 capability registry."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.registry import Registry

PKG = {
    "provenance": {"repository": "owner/repo", "file_count": 5},
    "capabilities": [
        {"id": "c1", "name": "JSON proc", "ontology_type": "TOOL", "confidence": 0.9},
    ],
}


def _registry(tmpdir):
    return Registry(os.path.join(tmpdir, "reg.json"))


def test_register_starts_candidate():
    with tempfile.TemporaryDirectory() as td:
        r = _registry(td)
        entry = r.register(PKG)
        assert entry["status"] == "candidate", "must never auto-approve (D4)"
        assert entry["capability_count"] == 1


def test_cannot_register_empty():
    with tempfile.TemporaryDirectory() as td:
        r = _registry(td)
        try:
            r.register({"provenance": {}, "capabilities": []})
            assert False, "empty package should raise"
        except ValueError:
            pass


def test_approve_requires_human():
    with tempfile.TemporaryDirectory() as td:
        r = _registry(td)
        e = r.register(PKG)
        assert e["status"] == "candidate"
        a = r.approve(e["entry_id"], "owner")
        assert a["status"] == "approved"
        assert a["approved_by"] == "owner"
        assert "approved_at" in a


def test_list_filter_by_status():
    with tempfile.TemporaryDirectory() as td:
        r = _registry(td)
        e1 = r.register(PKG)
        e2 = r.register(PKG)
        r.approve(e1["entry_id"], "owner")
        cands = r.list(status="candidate")
        appr = r.list(status="approved")
        assert len(cands) == 1 and len(appr) == 1
        assert cands[0]["entry_id"] == e2["entry_id"]


def test_persists_and_reloads():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "reg.json")
        r = Registry(path)
        e = r.register(PKG)
        r.approve(e["entry_id"], "owner")
        r2 = Registry(path)
        assert r2.get(e["entry_id"])["status"] == "approved"


def test_get_missing_returns_none():
    with tempfile.TemporaryDirectory() as td:
        r = _registry(td)
        assert r.get("nope") is None


def test_approve_missing_raises():
    with tempfile.TemporaryDirectory() as td:
        r = _registry(td)
        try:
            r.approve("nope", "owner")
            assert False
        except KeyError:
            pass