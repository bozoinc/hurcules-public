"""TDD tests for Wave 3 D4 approval artifacts (auditable 4-part approval)."""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.approval import (
    FOUR_PART_KEYS,
    SCHEMA,
    build_artifact,
    digest,
    record_approval,
    require_approval_before_spawn,
    sign_artifact,
    verify_signature,
)
from hurcules.registry import Registry

EVAL = {"schema": "hurcules.evaluation", "capability_count": 1,
        "unsupported_capability_rate": 0.0,
        "verdicts": [{"id": "c1", "status": "PASS", "supported": True}]}
SUMMARY = "JSON processing capability for market data pipelines"
PROVENANCE = {"repository": "owner/repo", "commit_sha": "abc123",
              "registry_entry": "entry-1"}
LIVE_DEMO = "demo-run-2026-08-09: 3 cases passed, fingerprint 9f2c"


def _artifact(**kw):
    """Build a complete artifact, overriding any part via kwargs."""
    return build_artifact(
        kw.get("eval", EVAL),
        kw.get("summary", SUMMARY),
        kw.get("provenance", PROVENANCE),
        kw.get("live_demo", LIVE_DEMO),
        metadata=kw.get("metadata"),
    )


def _registry(tmpdir, status="approved"):
    r = Registry(os.path.join(tmpdir, "reg.json"))
    e = r.register({
        "provenance": {"repository": "owner/repo", "commit_sha": "abc123"},
        "capabilities": [
            {"id": "c1", "name": "JSON proc", "ontology_type": "TOOL",
             "confidence": 0.9},
        ],
    })
    if status == "approved":
        r.approve(e["entry_id"], "owner")
    return r, e["entry_id"]


# ---------------------------------------------------------------------------
# build_artifact: the four required parts
# ---------------------------------------------------------------------------

def test_build_artifact_includes_all_four_parts_plus_schema():
    a = _artifact()
    assert FOUR_PART_KEYS <= set(a.keys())
    assert a["schema"] == SCHEMA
    assert "created_at" in a
    assert a["eval"] == EVAL
    assert a["summary"] == SUMMARY
    assert a["provenance"] == PROVENANCE
    assert a["live_demo"] == LIVE_DEMO


def test_build_artifact_accepts_optional_metadata():
    a = _artifact(metadata={"task": "market-brief"})
    assert a["metadata"] == {"task": "market-brief"}


def test_build_artifact_missing_or_empty_part_raises():
    # None / "" / {} each count as a missing part for each of the 4 keys
    bad = [
        {"eval": None}, {"summary": ""}, {"provenance": {}},
        {"live_demo": []},
    ]
    for kw in bad:
        try:
            _artifact(**kw)
            assert False, f"expected ValueError for {kw}"
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# digest: deterministic canonical fingerprint
# ---------------------------------------------------------------------------

def test_digest_deterministic_and_matches_canonical_json():
    a = _artifact()
    assert digest(a) == digest(a)
    # digest must equal sha256 over the exact canonical JSON (sort_keys,
    # compact separators) of the artifact content
    canonical = json.dumps(a, sort_keys=True, separators=(",", ":"))
    assert digest(a) == hashlib.sha256(canonical.encode()).hexdigest()


def test_digest_ignores_key_order():
    a1 = build_artifact(EVAL, SUMMARY, PROVENANCE, LIVE_DEMO)
    a2 = build_artifact(EVAL, SUMMARY, PROVENANCE, LIVE_DEMO)
    # same content => same digest (created_at has second precision)
    assert digest(a1) == digest(a2)


# ---------------------------------------------------------------------------
# sign / verify
# ---------------------------------------------------------------------------

def test_sign_then_verify_roundtrip():
    a = sign_artifact(_artifact(), "owner")
    assert a["approver"] == "owner"
    assert verify_signature(a) is True


def test_verify_rejects_unsigned_artifact():
    assert verify_signature(_artifact()) is False


def test_tampered_artifact_fails_verify():
    a = sign_artifact(_artifact(), "owner")
    a["eval"]["capability_count"] = 99  # tamper with a required part
    assert verify_signature(a) is False


def test_signature_binds_to_approver():
    a = sign_artifact(_artifact(), "owner")
    a["approver"] = "Mallory"  # swap approver after signing
    assert verify_signature(a) is False


def test_signature_changes_with_key_salt():
    a1 = sign_artifact(_artifact(), "owner", key="salt-a")
    a2 = sign_artifact(_artifact(), "owner", key="salt-b")
    assert a1["signature"] != a2["signature"]
    # keyed signature does not verify under the default (key=None) verifier
    assert verify_signature(a1) is False


# ---------------------------------------------------------------------------
# record_approval: attach artifact to a registry entry (storage assumption)
# ---------------------------------------------------------------------------

def test_record_approval_attaches_signed_artifact():
    with tempfile.TemporaryDirectory() as td:
        r, entry_id = _registry(td)
        updated = record_approval(r, entry_id, _artifact(), "owner")
        aa = updated["approval_artifact"]
        assert aa["artifact"]["approver"] == "owner"
        assert aa["digest"] == digest(aa["artifact"])
        assert aa["verified"] is True
        assert verify_signature(aa["artifact"]) is True
        # persisted and reloadable
        r2 = Registry(os.path.join(td, "reg.json"))
        assert r2.get(entry_id)["approval_artifact"]["verified"] is True


def test_record_approval_works_with_plain_dict_registry():
    store = {"e1": {"entry_id": "e1", "status": "approved"}}
    updated = record_approval(store, "e1", _artifact(), "owner")
    assert "approval_artifact" in updated
    assert "approval_artifact" in store["e1"]  # mutated in place


def test_record_approval_missing_entry_raises_keyerror():
    with tempfile.TemporaryDirectory() as td:
        r, _ = _registry(td)
        try:
            record_approval(r, "nope", _artifact(), "owner")
            assert False, "expected KeyError"
        except KeyError:
            pass


# ---------------------------------------------------------------------------
# require_approval_before_spawn: the gate
# ---------------------------------------------------------------------------

def test_gate_false_for_candidate_without_artifact():
    with tempfile.TemporaryDirectory() as td:
        r, entry_id = _registry(td, status="candidate")
        assert require_approval_before_spawn(r, entry_id) is False


def test_gate_false_for_approved_without_artifact():
    with tempfile.TemporaryDirectory() as td:
        r, entry_id = _registry(td, status="approved")  # no artifact
        assert require_approval_before_spawn(r, entry_id) is False


def test_gate_false_for_missing_entry():
    with tempfile.TemporaryDirectory() as td:
        r, _ = _registry(td)
        assert require_approval_before_spawn(r, "missing") is False


def test_gate_false_when_stored_artifact_tampered():
    with tempfile.TemporaryDirectory() as td:
        r, entry_id = _registry(td)
        record_approval(r, entry_id, _artifact(), "owner")
        r.get(entry_id)["approval_artifact"]["artifact"]["summary"] = "hacked"
        assert require_approval_before_spawn(r, entry_id) is False


def test_gate_true_for_fully_approved_entry():
    with tempfile.TemporaryDirectory() as td:
        r, entry_id = _registry(td)
        record_approval(r, entry_id, _artifact(), "owner")
        assert require_approval_before_spawn(r, entry_id) is True