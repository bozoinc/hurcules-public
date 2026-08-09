"""Tests for Stage 8.4 discovery queue (dedupe + allow/deny + budget)."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.discovery_queue import (
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_SKIPPED,
    QueueState,
    filter_candidates,
    load_state,
    mark,
    per_repo_timeout,
    plan_sweep,
)

AT = "2026-01-01T00:00:00+00:00"


class _Obj:
    """Minimal object with a .repo attribute (stands in for discovery.Candidate)."""

    def __init__(self, repo):
        self.repo = repo


def _state(done=(), failed=(), queued=(), skipped=()):
    s = {}
    for r in done:
        s[r] = {"status": STATUS_DONE, "at": AT}
    for r in failed:
        s[r] = {"status": STATUS_FAILED, "at": AT}
    for r in queued:
        s[r] = {"status": STATUS_QUEUED, "at": AT}
    for r in skipped:
        s[r] = {"status": STATUS_SKIPPED, "at": AT}
    return s


def _cands(*repos):
    return [{"repo": r} for r in repos]


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


def test_load_state_missing_file_returns_empty(tmp_path):
    assert load_state(tmp_path / "nope.json") == {}


def test_mark_persists_and_reload(tmp_path):
    store = tmp_path / "state.json"
    mark(store, "a/one", STATUS_DONE)
    mark(store, "b/two", STATUS_FAILED)
    state = load_state(store)
    assert state["a/one"]["status"] == STATUS_DONE
    assert state["b/two"]["status"] == STATUS_FAILED
    assert state["a/one"]["at"]  # non-empty timestamp
    assert store.exists()


def test_mark_upserts_status(tmp_path):
    store = tmp_path / "state.json"
    mark(store, "a/one", STATUS_DONE)
    mark(store, "a/one", STATUS_QUEUED)
    state = load_state(store)
    assert state["a/one"]["status"] == STATUS_QUEUED
    assert len(state) == 1  # upsert, not duplicate


def test_mark_writes_sorted_deterministic_json(tmp_path):
    store = tmp_path / "state.json"
    mark(store, "b/two", STATUS_FAILED)
    mark(store, "a/one", STATUS_DONE)
    text = store.read_text()
    # outer keys and inner keys sorted -> byte-stable layout for diffs
    assert text.index('"a/one"') < text.index('"b/two"')
    assert text.index('"at"') < text.index('"status"')
    assert json.loads(text) == load_state(store)


def test_load_state_corrupt_json_returns_empty(tmp_path):
    store = tmp_path / "state.json"
    store.write_text("{not json")
    assert load_state(store) == {}


# ---------------------------------------------------------------------------
# filter_candidates: dedupe + allow/deny
# ---------------------------------------------------------------------------


def test_filter_skips_done_and_failed(tmp_path):
    state = _state(done=("a/done",), failed=("b/bad",))
    out = filter_candidates(_cands("a/done", "b/bad", "c/fresh"), state)
    assert [c["repo"] for c in out] == ["c/fresh"]


def test_filter_keeps_queued_and_skipped():
    state = _state(queued=("a/queued",), skipped=("b/skipped",))
    out = filter_candidates(_cands("a/queued", "b/skipped"), state)
    assert [c["repo"] for c in out] == ["a/queued", "b/skipped"]


def test_filter_allow_list():
    cands = _cands("a/x", "b/y", "c/z")
    out = filter_candidates(cands, {}, allow={"b/y"})
    assert [c["repo"] for c in out] == ["b/y"]


def test_filter_deny_list():
    cands = _cands("a/x", "b/y", "c/z")
    out = filter_candidates(cands, {}, deny={"a/x", "c/z"})
    assert [c["repo"] for c in out] == ["b/y"]


def test_filter_allow_and_deny_combined():
    cands = _cands("a/x", "b/y", "c/z")
    out = filter_candidates(cands, {}, allow={"a/x", "b/y"}, deny={"b/y"})
    assert [c["repo"] for c in out] == ["a/x"]


def test_filter_empty_allow_or_deny_is_noop():
    cands = _cands("a/x", "b/y")
    assert filter_candidates(cands, {}, allow=[]) == cands
    assert filter_candidates(cands, {}, deny=set()) == cands


def test_filter_handles_dicts_and_objects():
    cands = [{"repo": "a/done"}, _Obj("b/bad"), _Obj("c/fresh")]
    state = _state(done=("a/done",), failed=("b/bad",))
    out = filter_candidates(cands, state)
    assert len(out) == 1
    assert isinstance(out[0], _Obj)  # original objects preserved
    assert out[0].repo == "c/fresh"


def test_filter_preserves_input_order():
    cands = _cands("c/z", "a/x", "b/y")
    out = filter_candidates(cands, {}, allow={"a/x", "b/y", "c/z"})
    assert [c["repo"] for c in out] == ["c/z", "a/x", "b/y"]


# ---------------------------------------------------------------------------
# plan_sweep: counts + budget
# ---------------------------------------------------------------------------


def test_plan_sweep_counts_skips():
    state = _state(done=("a/done", "b/done"), failed=("c/bad",))
    plan = plan_sweep(_cands("a/done", "b/done", "c/bad", "d/new", "e/new"), state)
    assert [c["repo"] for c in plan["to_run"]] == ["d/new", "e/new"]
    assert plan["skipped_done"] == 2
    assert plan["skipped_failed"] == 1
    assert plan["skipped_allow_deny"] == 0
    assert plan["budget_used"] is False


def test_plan_sweep_no_budget_runs_all():
    state = _state(failed=("a/bad",))
    plan = plan_sweep(_cands("a/bad", "b/x"), state)
    assert [c["repo"] for c in plan["to_run"]] == ["b/x"]
    assert plan["budget_used"] is False


def test_plan_sweep_budget_truncates():
    plan = plan_sweep(_cands("a", "b", "c", "d", "e"), {}, budget=2)
    assert [c["repo"] for c in plan["to_run"]] == ["a", "b"]
    assert plan["budget_used"] is True


def test_plan_sweep_budget_not_exceeded():
    plan = plan_sweep(_cands("a", "b"), {}, budget=5)
    assert [c["repo"] for c in plan["to_run"]] == ["a", "b"]
    assert plan["budget_used"] is False


def test_plan_sweep_budget_zero():
    plan = plan_sweep(_cands("a", "b"), {}, budget=0)
    assert plan["to_run"] == []
    assert plan["budget_used"] is True


def test_plan_sweep_budget_counts_skips_then_truncates():
    state = _state(done=("a", "b"))
    plan = plan_sweep(_cands("a", "b", "c", "d", "e"), state, budget=1)
    assert [c["repo"] for c in plan["to_run"]] == ["c"]
    assert plan["skipped_done"] == 2
    assert plan["budget_used"] is True


# ---------------------------------------------------------------------------
# Per-repo timeout seam + QueueState shape
# ---------------------------------------------------------------------------


def test_per_repo_timeout_defaults():
    assert per_repo_timeout("a/x") == 120
    assert per_repo_timeout("a/x", base=60) == 60


def test_per_repo_timeout_extra_per_file():
    assert per_repo_timeout("a/x", extra_per_file=5) == 125
    assert per_repo_timeout("a/x", base=60, extra_per_file=5) == 65


def test_queue_state_shape():
    qs = QueueState(repo="a/x", status=STATUS_DONE, at=AT)
    assert qs.to_dict() == {"repo": "a/x", "status": STATUS_DONE, "at": AT}
