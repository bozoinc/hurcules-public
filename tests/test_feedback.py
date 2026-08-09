"""TDD tests for W3-[9] feedback recorder."""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.feedback import (  # noqa: E402
    FeedbackRecord,
    attach_to_package,
    package_feedback_history,
    record_feedback,
    summarize,
)

PKG = {
    "provenance": {"repository": "owner/repo", "file_count": 5},
    "capabilities": [
        {"id": "c1", "name": "JSON proc", "ontology_type": "TOOL", "confidence": 0.9},
    ],
}


def _store(tmpdir):
    return os.path.join(tmpdir, "feedback.json")


def _rec(cap, event="eval", outcome="pass", detail="", ts=None, source="fleet-run-abc"):
    return FeedbackRecord(
        capability_id=cap,
        package_id="owner/repo",
        event=event,
        outcome=outcome,
        detail=detail,
        ts=ts or "",
        source=source,
    )


def test_record_then_history() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", ts="2026-01-01T00:00:00Z"))
        hist = package_feedback_history(store, "c1")
        assert len(hist) == 1
        assert hist[0]["capability_id"] == "c1"
        assert hist[0]["event"] == "eval"
        assert hist[0]["outcome"] == "pass"


def test_unknown_capability_returns_empty() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", ts="2026-01-01T00:00:00Z"))
        assert package_feedback_history(store, "nope") == []


def test_history_sorted_by_ts() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", ts="2026-01-03T00:00:00Z"))
        record_feedback(store, _rec("c1", ts="2026-01-01T00:00:00Z"))
        record_feedback(store, _rec("c1", ts="2026-01-02T00:00:00Z"))
        ts = [r["ts"] for r in package_feedback_history(store, "c1")]
        assert ts == sorted(ts)
        assert ts[0] == "2026-01-01T00:00:00Z"


def test_two_capabilities_isolated() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", ts="2026-01-01T00:00:00Z"))
        record_feedback(store, _rec("c2", ts="2026-01-02T00:00:00Z"))
        assert len(package_feedback_history(store, "c1")) == 1
        assert len(package_feedback_history(store, "c2")) == 1


def test_missing_ts_defaults_to_now() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1"))
        assert package_feedback_history(store, "c1")[0]["ts"] != ""


def test_summarize_counts_and_pass_rate() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", outcome="pass", ts="2026-01-01T00:00:00Z"))
        record_feedback(store, _rec("c1", outcome="pass", ts="2026-01-02T00:00:00Z"))
        record_feedback(store, _rec("c1", outcome="fail", ts="2026-01-03T00:00:00Z"))
        s = summarize(store, "c1")
        assert s["events"] == 3
        assert s["pass_rate"] == pytest.approx(2 / 3, abs=1e-4)
        assert s["usages"] == 0
        assert s["flags"] == []
        assert s["edge_cases"] == []


def test_summarize_empty_store_is_safe() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        s = summarize(store, "ghost")  # store file doesn't even exist yet
        assert s == {
            "events": 0,
            "pass_rate": 0.0,
            "flags": [],
            "usages": 0,
            "edge_cases": [],
        }


def test_summarize_usages_from_spawns() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", event="spawn", outcome="pass", ts="2026-01-01T00:00:00Z"))
        record_feedback(store, _rec("c1", event="spawn", outcome="fail", ts="2026-01-02T00:00:00Z"))
        record_feedback(store, _rec("c1", outcome="pass", ts="2026-01-03T00:00:00Z"))
        s = summarize(store, "c1")
        assert s["usages"] == 2
        assert s["pass_rate"] == pytest.approx(2 / 3, abs=1e-4)


def test_summarize_flags_and_edge_cases() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", event="flag", outcome="flag",
                                    detail="secret-reference in workflow",
                                    ts="2026-01-01T00:00:00Z"))
        record_feedback(store, _rec("c1", event="flag", outcome="flag",
                                    detail="hardcoded path", ts="2026-01-02T00:00:00Z"))
        record_feedback(store, _rec("c1", outcome="pass", ts="2026-01-03T00:00:00Z"))
        s = summarize(store, "c1")
        assert sorted(s["flags"]) == ["hardcoded path", "secret-reference in workflow"]
        assert sorted(s["edge_cases"]) == ["hardcoded path", "secret-reference in workflow"]
        assert s["events"] == 3
        assert s["pass_rate"] == pytest.approx(1 / 3, abs=1e-4)


def test_attach_to_package_does_not_mutate() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", outcome="pass", ts="2026-01-01T00:00:00Z"))
        before = json.dumps(PKG, sort_keys=True)
        attached = attach_to_package(PKG, store, "c1")
        after = json.dumps(PKG, sort_keys=True)
        assert before == after, "original package must not change"
        assert "feedback" not in PKG
        assert "feedback" in attached
        assert attached["feedback"]["pass_rate"] == 1.0


def test_attach_to_package_is_deep_copy() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        attached = attach_to_package(PKG, store, "c1")
        assert attached is not PKG
        assert attached["capabilities"] is not PKG["capabilities"]
        attached["capabilities"][0]["id"] = "mutated"
        assert PKG["capabilities"][0]["id"] == "c1"


def test_deterministic_two_identical_runs() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", outcome="pass", ts="2026-01-01T00:00:00Z"))
        record_feedback(store, _rec("c1", outcome="fail", ts="2026-01-02T00:00:00Z"))
        s1 = summarize(store, "c1")
        s2 = summarize(store, "c1")
        assert s1 == s2
        assert json.dumps(s1, sort_keys=True) == json.dumps(s2, sort_keys=True)


def test_store_file_has_deterministic_json() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        record_feedback(store, _rec("c1", outcome="fail", ts="2026-01-02T00:00:00Z"))
        record_feedback(store, _rec("c1", outcome="pass", ts="2026-01-01T00:00:00Z"))
        with open(store, "r") as fh:
            parsed = json.load(fh)
        assert sorted(parsed.keys()) == ["c1"]
        assert [r["ts"] for r in parsed["c1"]] == [
            "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"]


def test_rejects_bad_event_and_outcome() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = _store(td)
        for bad in [
            _rec("c1", event="wat", outcome="pass"),
            _rec("c1", event="eval", outcome="wat"),
        ]:
            try:
                record_feedback(store, bad)
                assert False, "invalid record should raise"
            except ValueError:
                pass
        assert package_feedback_history(store, "c1") == []