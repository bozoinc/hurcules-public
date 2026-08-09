"""TDD tests for Stage 8 Discovery (ranking + gh fetch)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.discovery import (
    Candidate,
    _license_signal,
    _score_candidate,
    gh_search,
    clone_candidate,
    rank_candidates,
    top,
)


# ---------------------------------------------------------------------------
# License signal
# ---------------------------------------------------------------------------


def test_license_signal_classification():
    assert _license_signal("MIT") == "permissive"
    assert _license_signal("Apache-2.0") == "permissive"
    assert _license_signal("GPL-3.0") == "restrictive"
    assert _license_signal("AGPL-3.0") == "restrictive"
    assert _license_signal("proprietary") == "restrictive"
    assert _license_signal("") == "unknown"


# ---------------------------------------------------------------------------
# Ranking (pure, deterministic)
# ---------------------------------------------------------------------------


def _mk(repo, stars=0, pushed="", lic="MIT", lang="py", size=500_000):
    return Candidate(repo=repo, stars=stars, pushed_at=pushed,
                     license_spdx=lic, language=lang, size_bytes=size)


def test_permissive_outranks_restrictive():
    base = "2026-01-01T00:00:00Z"
    permissive = _mk("a/perm", stars=500, pushed=base, lic="MIT")
    restrictive = _mk("b/gpl", stars=500, pushed=base, lic="GPL-3.0")
    ranked = rank_candidates([restrictive, permissive])
    assert ranked[0].repo == "a/perm"


def test_active_outranks_stale():
    recent = _mk("a/recent", pushed="2026-07-01T00:00:00Z")
    stale = _mk("b/stale", pushed="2020-01-01T00:00:00Z")
    ranked = rank_candidates([stale, recent])
    assert ranked[0].repo == "a/recent"


def test_stars_break_ties_recently():
    recent = "2026-06-01T00:00:00Z"
    popular = _mk("a/pop", stars=8000, pushed=recent)
    small = _mk("b/small", stars=50, pushed=recent)
    ranked = rank_candidates([small, popular])
    assert ranked[0].repo == "a/pop"


def test_ranking_deterministic():
    cs = [_mk("a/x", stars=30), _mk("b/y", stars=12), _mk("c/z", stars=900)]
    assert rank_candidates(cs) == rank_candidates(cs)


def test_top_limits_count_and_order():
    cs = [_mk(f"r/{i}", stars=i * 100) for i in range(5)]
    t = top(cs, 3)
    assert len(t) == 3
    assert t[0].stars > t[1].stars > t[2].stars


def test_from_gh_item_maps_fields():
    item = {
        "full_name": "octo/cat",
        "stargazers_count": 1234,
        "pushed_at": "2026-07-15T12:00:00Z",
        "license": {"spdx_id": "MIT"},
        "language": "Python",
        "size": 9000,
    }
    c = Candidate.from_gh_item(item)
    assert c.repo == "octo/cat"
    assert c.stars == 1234
    assert c.license_spdx == "mit"


# ---------------------------------------------------------------------------
# gh fetch (mocked)
# ---------------------------------------------------------------------------


def test_gh_search_parses_items():
    payload = {
        "items": [
            {"full_name": "o/r1", "stargazers_count": 5,
             "license": {"spdx_id": "MIT"}},
            {"full_name": "o/r2", "stargazers_count": 99,
             "license": {"spdx_id": "Apache-2.0"}},
        ]
    }
    import json
    fake_shell = lambda q: (0, json.dumps(payload), "")
    found = gh_search("agent", limit=2, shell=fake_shell)
    assert len(found) == 2
    assert found[0].repo == "o/r1"


def test_gh_search_returns_empty_on_error():
    fake_shell = lambda q: (1, "", "boom")
    assert gh_search("x", shell=fake_shell) == []


def test_gh_search_empty_items():
    fake_shell = lambda q: (0, '{"items": []}', "")
    assert gh_search("x", shell=fake_shell) == []


def test_clone_candidate_calls_git(monkeypatch):
    class P:
        returncode = 0
    monkeypatch.setattr("subprocess.run", lambda cmd, **kw: P())
    assert clone_candidate("o/r", "/tmp/dest") is True


def test_clone_candidate_fail_on_rc(monkeypatch):
    class P:
        returncode = 1
    monkeypatch.setattr("subprocess.run", lambda cmd, **kw: P())
    assert clone_candidate("o/r", "/tmp/dest") is False