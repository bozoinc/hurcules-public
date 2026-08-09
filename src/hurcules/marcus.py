"""HURCULES Wave 4 [16] — Marcus, the novice UX step-machine.

A guided surface for NON-CODERS: submit a repo URL, review the report,
approve, and get a capability — no terminal, no code. This module holds
the interaction logic (a strict step machine) plus `run_novice`, an
automated 'novice persona' script that clicks through every step exactly
like a human would, so the whole flow is provable end-to-end with zero
human input.

Deterministic core: `ingest_fn` is injectable (e.g. the real pipeline
ingest from scripts/discovery_to_pipeline.py); when it is None the ingest
step uses a simulated stub report, so tests and offline demos run with
no network at all. The approve step bundles the D4 approval artifact via
hurcules.approval.build_artifact (deterministic content; created_at is
the only time-varying field).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlparse

from hurcules.approval import build_artifact, digest

STEPS = ["submit", "ingest", "review", "approve", "done"]

# Only these hosts (or genuine subdomains of them) are acceptable targets.
_ALLOWED_HOSTS = ("github.com", "gitlab.com")

APPROVER = "novice"


@dataclass
class MarcusSession:
    """State of one novice's journey through the Marcus flow."""

    repo_url: str
    step: str = "submit"
    report: dict | None = None   # ingestion report shown at the review screen
    result: dict | None = None   # approval artifact once the novice approves
    errors: list[str] = field(default_factory=list)


def new_session(repo_url: str) -> MarcusSession:
    """Start a fresh Marcus session at the submit step."""
    return MarcusSession(repo_url=repo_url)


def validate_url(url: str) -> bool:
    """Hostile-by-default repo URL check.

    Accepts only http(s) URLs on github.com / gitlab.com (or a subdomain)
    with an owner/repo path. Rejects everything else: garbage, file://,
    credentials embedded in the URL, unknown hosts, bare hosts with no repo
    path.
    """
    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.username or parsed.password:  # credentials in a URL: hostile
        return False
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS and not host.endswith(
            (".github.com", ".gitlab.com")):
        return False
    # A repo URL must name at least owner/repo.
    segments = [s for s in parsed.path.split("/") if s]
    return len(segments) >= 2


def _simulated_report(repo_url: str) -> dict:
    """Stub report used when no ingest_fn is injected (tests / offline demo)."""
    return {
        "repo": repo_url,
        "ok": True,
        "simulated": True,
        "capabilities": ["automated capability extraction", "risk screening"],
        "security_notes": ["no credentials detected", "license gate passed"],
    }


def run_step(session: MarcusSession, action: str,
             ingest_fn: Callable[[str], dict] | None = None) -> MarcusSession:
    """Advance the session by one guided step. Mutates and returns `session`.

    The only valid action at any step is the step's own name, so a novice
    (or the automated persona) can only move forward one screen at a time:
    submit -> ingest -> review -> approve -> done. Invalid actions and
    ingest failures record an error and leave the session where it is —
    the machine never crashes, never guesses.
    """
    if session.step == "done":
        session.errors.append(f"session already finished; '{action}' ignored")
        return session
    if action != session.step:
        session.errors.append(f"cannot '{action}' at step '{session.step}'")
        return session

    if session.step == "submit":
        if validate_url(session.repo_url):
            session.step = "ingest"
        else:
            session.errors.append(
                f"invalid repository URL: {session.repo_url!r}")

    elif session.step == "ingest":
        error = None
        report = None
        if ingest_fn is None:
            report = _simulated_report(session.repo_url)
        else:
            try:
                report = ingest_fn(session.repo_url)
            except Exception as exc:  # hostile-by-default: never crash
                error = f"ingest failed: {exc}"
        if report is None:
            error = error or "ingest returned no report"
        elif not isinstance(report, dict):
            error = f"ingest returned unexpected result: {type(report).__name__}"
        elif report.get("ok") is False:
            error = f"ingest failed: {report.get('error') or 'unknown reason'}"
        if error:
            session.errors.append(error)
            session.report = None
            session.step = "submit"  # novice gets to fix the URL / retry
        else:
            session.report = report
            session.step = "review"

    elif session.step == "review":
        if session.report is None:
            session.errors.append("no report to review")
        else:
            session.step = "approve"  # report is shown; advancing is a no-op

    elif session.step == "approve":
        if session.report is None:
            session.errors.append("no report to approve")
            return session
        artifact = build_artifact(
            eval_result={
                "ok": session.report.get("ok", True),
                "capability_count": len(session.report.get("capabilities", [])),
                "simulated": bool(session.report.get("simulated", False)),
            },
            summary=f"Novice-approved capability package from {session.repo_url}",
            provenance={"repo": session.repo_url, "source": "marcus-novice-ux"},
            live_demo=("simulated" if session.report.get("simulated")
                       else "ingest-pipeline"),
            metadata={"flow": "marcus", "approver": APPROVER},
        )
        session.result = {
            "approved": True,
            "artifact": artifact,
            "digest": digest(artifact),
        }
        session.step = "done"
    return session


def run_novice(repo_url: str, ingest_fn: Callable[[str], dict] | None = None,
               approve: bool = True) -> MarcusSession:
    """Automated 'novice persona' — clicks every screen like a non-coder.

    Walks submit -> ingest -> review -> approve exactly as a human would,
    proving the whole flow end-to-end with zero human input and no network
    unless a real ingest_fn is injected. With approve=False the persona
    reads the report and stops at the review screen — a cautious novice
    who never clicks approve.
    """
    session = new_session(repo_url)
    run_step(session, "submit")
    run_step(session, "ingest", ingest_fn)
    if not approve:
        return session  # review screen: report is visible, nothing approved
    run_step(session, "review")
    run_step(session, "approve")
    return session
