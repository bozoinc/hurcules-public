"""Tests for registry lifecycle states + stale detection (lifecycle.py)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.registry import Registry
from hurcules.lifecycle import (
    LifecycleManager,
    VALID_STATES,
    is_stale,
    list_by_state,
    mark_stale,
)

PKG = {
    "provenance": {"repository": "owner/repo", "file_count": 5},
    "capabilities": [
        {"id": "c1", "name": "JSON proc", "ontology_type": "TOOL", "confidence": 0.9},
    ],
}


def _registry(td, sha="abc123"):
    r = Registry(os.path.join(td, "reg.json"))
    e = r.register(PKG, commit_sha=sha)
    return r, e


def _manager(td, sha="abc123"):
    r, e = _registry(td, sha)
    return LifecycleManager(r), e


def test_valid_states_exact():
    assert VALID_STATES == {
        "candidate", "approved", "deprecated", "revoked", "superseded",
    }


def test_candidate_to_approved_succeeds_with_audit():
    with tempfile.TemporaryDirectory() as td:
        mgr, e = _manager(td)
        out = mgr.transition(e["entry_id"], "approved", "owner", "looks good")
        assert out["status"] == "approved"
        assert len(out["audit_trail"]) == 1
        rec = out["audit_trail"][0]
        assert rec["state"] == "approved"
        assert rec["by"] == "owner"
        assert rec["reason"] == "looks good"
        assert "at" in rec


def test_all_valid_chains_from_candidate():
    with tempfile.TemporaryDirectory() as td:
        mgr, e = _manager(td)
        eid = e["entry_id"]
        assert mgr.transition(eid, "revoked", "owner", "untrusted")["status"] == "revoked"


def test_approved_to_deprecated_and_deprecated_to_superseded():
    with tempfile.TemporaryDirectory() as td:
        r, e = _registry(td)
        r.approve(e["entry_id"], "owner")
        mgr = LifecycleManager(r)
        eid = e["entry_id"]
        assert mgr.transition(eid, "deprecated", "owner", "old")["status"] == "deprecated"
        assert mgr.transition(eid, "superseded", "Bo", "replaced")["status"] == "superseded"
        assert len(mgr._entry(eid)["audit_trail"]) == 2


def test_invalid_transition_raises_valueerror():
    with tempfile.TemporaryDirectory() as td:
        r, e = _registry(td)
        r.approve(e["entry_id"], "owner")
        mgr = LifecycleManager(r)
        eid = e["entry_id"]
        for bad in ("candidate", "approved"):  # backwards moves are invalid
            try:
                mgr.transition(eid, bad, "owner", "nope")
                assert False, f"approved -> {bad} should raise"
            except ValueError:
                pass


def test_terminal_states_are_locked():
    with tempfile.TemporaryDirectory() as td:
        mgr, e = _manager(td)
        eid = e["entry_id"]
        mgr.transition(eid, "revoked", "owner", "done")
        try:
            mgr.transition(eid, "deprecated", "owner", "no")
            assert False, "revoked -> deprecated should raise"
        except ValueError:
            pass


def test_invalid_state_name_raises():
    with tempfile.TemporaryDirectory() as td:
        mgr, e = _manager(td)
        try:
            mgr.transition(e["entry_id"], "banana", "owner", "bad")
            assert False, "unknown state should raise"
        except ValueError:
            pass


def test_unknown_entry_raises_keyerror():
    with tempfile.TemporaryDirectory() as td:
        mgr, _ = _manager(td)
        try:
            mgr.transition("missing", "approved", "owner", "x")
            assert False, "missing entry should raise KeyError"
        except KeyError:
            pass


def test_is_stale_true_when_sha_differs():
    with tempfile.TemporaryDirectory() as td:
        r, e = _registry(td, sha="oldsha")
        r.approve(e["entry_id"], "owner")
        assert is_stale(r.get(e["entry_id"]), "newsha") is True


def test_is_stale_false_when_sha_matches():
    with tempfile.TemporaryDirectory() as td:
        _, e = _registry(td, sha="same")
        assert is_stale(e, "same") is False


def test_is_stale_false_when_not_live():
    with tempfile.TemporaryDirectory() as td:
        mgr, e = _manager(td, sha="oldsha")
        mgr.transition(e["entry_id"], "deprecated", "owner", "retired")
        assert is_stale(mgr._entry(e["entry_id"]), "newsha") is False


def test_mark_stale_deprecates_with_reason():
    with tempfile.TemporaryDirectory() as td:
        r, e = _registry(td, sha="oldsha")
        r.approve(e["entry_id"], "owner")
        out = mark_stale(e["entry_id"], "newsha", "Watcher", r)
        assert out["status"] == "deprecated"
        assert "oldsha->newsha" in out["audit_trail"][0]["reason"]


def test_mark_stale_noop_when_fresh():
    with tempfile.TemporaryDirectory() as td:
        r, e = _registry(td, sha="same")
        out = mark_stale(e["entry_id"], "same", "Watcher", r)
        assert out["status"] == "candidate"
        assert "audit_trail" not in out


def test_list_by_state_filters():
    with tempfile.TemporaryDirectory() as td:
        r, e1 = _registry(td)
        e2 = r.register(PKG)
        r.approve(e1["entry_id"], "owner")
        assert len(list_by_state(r, "candidate")) == 1
        assert list_by_state(r, "candidate")[0]["entry_id"] == e2["entry_id"]
        assert len(list_by_state(r, "approved")) == 1
        assert len(list_by_state(r, "deprecated")) == 0


def test_state_and_audit_persist_after_reload():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "reg.json")
        r = Registry(path)
        e = r.register(PKG, commit_sha="oldsha")
        r.approve(e["entry_id"], "owner")
        mark_stale(e["entry_id"], "newsha", "Watcher", r)
        r2 = Registry(path)
        got = r2.get(e["entry_id"])
        assert got["status"] == "deprecated"
        assert got["audit_trail"][0]["reason"] == "upstream commit changed: oldsha->newsha"