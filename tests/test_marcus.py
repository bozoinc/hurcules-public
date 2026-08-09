"""Tests for the Marcus novice UX step-machine (src/hurcules/marcus.py).

Covers: URL validation (hostile-by-default), the step machine's
submit/ingest/review/approve/done transitions, error containment, and the
automated run_novice 'novice persona' script. All ingest is stubbed —
no network anywhere.
"""
from hurcules.marcus import (
    STEPS,
    MarcusSession,
    new_session,
    run_novice,
    run_step,
    validate_url,
)

URL = "https://github.com/octocat/Hello-World"


def _stub_ingest(repo_url):
    """Deterministic stand-in for the real pipeline ingest."""
    return {
        "repo": repo_url,
        "ok": True,
        "capabilities": ["cap-a", "cap-b"],
        "security_notes": ["clean"],
    }


# ---------------------------------------------------------------- validate_url

def test_validate_url_accepts_github_and_gitlab():
    assert validate_url("https://github.com/octocat/Hello-World")
    assert validate_url("https://gitlab.com/gitlab-org/gitlab")
    assert validate_url("http://github.com/owner/repo")
    assert validate_url("https://gitlab.com/group/subgroup/repo")


def test_validate_url_rejects_garbage_and_bad_scheme():
    for bad in ["not a url", "", "   ", "github.com/owner/repo",
                "htp://github.com/o/r", "https://", 42, None]:
        assert not validate_url(bad)


def test_validate_url_rejects_file_and_credentials():
    assert not validate_url("file:///etc/passwd")
    assert not validate_url("file://github.com/owner/repo")
    assert not validate_url("https://user:pass@github.com/owner/repo")
    assert not validate_url("https://token@gitlab.com/group/repo")


def test_validate_url_rejects_unknown_and_bare_hosts():
    assert not validate_url("https://example.com/owner/repo")
    assert not validate_url("https://github.com")
    assert not validate_url("https://github.com/owner")
    assert not validate_url("https://github.com.evil.com/owner/repo")


# ------------------------------------------------------------- step machine

def test_new_session_starts_at_submit():
    s = new_session(URL)
    assert isinstance(s, MarcusSession)
    assert s.step == "submit"
    assert s.report is None
    assert s.result is None
    assert s.errors == []
    assert STEPS == ["submit", "ingest", "review", "approve", "done"]


def test_submit_valid_url_advances_to_ingest():
    s = run_step(new_session(URL), "submit")
    assert s.step == "ingest"
    assert s.errors == []


def test_submit_invalid_url_records_error_and_stays():
    s = run_step(new_session("https://example.com/o/r"), "submit")
    assert s.step == "submit"
    assert len(s.errors) == 1
    assert "invalid repository URL" in s.errors[0]


def test_wrong_action_records_error_and_stays():
    s = new_session(URL)
    run_step(s, "ingest")  # at 'submit' the only valid action is 'submit'
    assert s.step == "submit"
    assert "cannot 'ingest' at step 'submit'" in s.errors[0]


def test_ingest_with_stub_fn_advances_to_review():
    s = new_session(URL)
    run_step(s, "submit")
    run_step(s, "ingest", _stub_ingest)
    assert s.step == "review"
    assert s.report == _stub_ingest(URL)
    assert s.errors == []


def test_ingest_default_is_simulated_report():
    s = new_session(URL)
    run_step(s, "submit")
    run_step(s, "ingest")  # no fn -> simulated stub, no network
    assert s.step == "review"
    assert s.report is not None
    assert s.report["ok"] is True
    assert s.report["simulated"] is True
    assert "capabilities" in s.report
    assert "security_notes" in s.report


def test_ingest_failure_returns_to_submit_with_error():
    def failing(repo_url):
        return {"repo": repo_url, "ok": False, "error": "clone failed"}

    def raising(repo_url):
        raise RuntimeError("boom")

    for bad_fn in (failing, raising):
        s = new_session(URL)
        run_step(s, "submit")
        run_step(s, "ingest", bad_fn)
        assert s.step == "submit"
        assert s.report is None
        assert s.errors, "failure must be recorded"


def test_approve_builds_artifact_and_reaches_done():
    s = new_session(URL)
    run_step(s, "submit")
    run_step(s, "ingest", _stub_ingest)
    run_step(s, "review")
    assert s.step == "approve"
    run_step(s, "approve")
    assert s.step == "done"
    assert s.result is not None
    assert s.result["approved"] is True
    assert s.result["digest"]
    artifact = s.result["artifact"]
    for part in ("eval", "summary", "provenance", "live_demo"):
        assert artifact[part]
    assert artifact["provenance"]["repo"] == URL
    assert artifact["metadata"]["approver"] == "novice"
    # 'done' is terminal: further actions are ignored with an error
    run_step(s, "approve")
    assert s.step == "done"
    assert "already finished" in s.errors[-1]


# ------------------------------------------------------------ novice persona

def test_run_novice_completes_all_five_steps():
    # both the injected stub and the default simulated ingest must
    # complete the whole flow end-to-end, deterministically
    for ingest_fn in (None, _stub_ingest):
        s = run_novice(URL, ingest_fn=ingest_fn)
        assert s.step == "done"
        assert s.report is not None
        assert s.result is not None
        assert s.result["approved"] is True
        assert s.errors == []
        # deterministic core: repeated runs agree on every content field
        again = run_novice(URL, ingest_fn=ingest_fn)
        assert again.step == "done"
        assert again.report is not None
        assert again.result is not None
        assert again.report == s.report
        assert again.errors == []
        for part in ("eval", "summary", "provenance", "live_demo"):
            assert again.result["artifact"][part] == s.result["artifact"][part]


def test_run_novice_without_approval_stops_at_review():
    s = run_novice(URL, ingest_fn=_stub_ingest, approve=False)
    assert s.step == "review"
    assert s.report is not None
    assert s.result is None
    assert s.errors == []


def test_run_novice_bad_url_stays_at_submit_with_errors():
    s = run_novice("https://example.com/o/r")
    assert s.step == "submit"
    assert s.errors
    assert s.result is None
