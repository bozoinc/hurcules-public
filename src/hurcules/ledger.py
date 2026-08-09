"""Wave 0 [14] — cost & duration ledger.

Records ONE JSON run-report per pipeline run: per-stage model, route,
prompt/completion tokens, latency, and wall-clock duration. Persists to
data/run-reports/<run_id>.json. Makes the real per-stage cost visible
instead of a single headline number.

Public seam: RunReport
    rpt = RunReport(repo="owner/name", run_id=ts)
    client = make_openai_client(...)          # unchanged
    with rpt.stage("map"):
        m = map_repository(...)
    with rpt.stage("analyst", client):
        analysis = analyze(m, client)
    rpt.save(ROOT/"data"/"run-reports")
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def attach_usage(chat: Callable, model: str, base_url: str) -> Callable:
    """Attach a live .last_usage dict to a chat callable (idempotent).

    Existing callers keep exactly the same contract (list[dict] -> str); new
    callers read chat.last_usage for tokens/latency after each call. The
    current api returns only content so token counts are unavailable from the
    provider seam — the ledger records messages, latency, model, route and
    leaves tokens as 0 pending a provider-usage upgrade (see ISSUE-013).
    """
    if getattr(chat, "_ledger_usage", None) is not None:
        return chat

    state = {"last_usage": {"model": model, "base_url": base_url}}

    def wrapper(messages):  # same contract: list[dict] -> str
        start = time.monotonic()
        try:
            content = chat(messages)
            ok = True
        except BaseException as e:
            content = ""
            ok = False
            err = e
        dur = time.monotonic() - start
        # mutate the SAME dict object in place so wrapper.last_usage (set
        # below) stays a live reference that reflects the latest call
        state["last_usage"].update({
            "model": model,
            "base_url": base_url,
            "messages": len(messages),
            "latency_s": round(dur, 3),
            "ok": ok,
        })
        if not ok:
            raise err
        return content

    wrapper.last_usage = state["last_usage"]  # type: ignore[attr-defined]
    wrapper._ledger_usage = state  # type: ignore[attr-defined]
    return wrapper


class RunReport:
    """Collects per-stage metrics and writes one JSON run-report."""

    SCHEMA_VERSION = 1

    def __init__(self, repo: str = "unknown", run_id: Optional[str] = None):
        self.repo = repo
        self.run_id = run_id or _now_utc().replace(":", "-")
        self.started = _now_utc()
        self._lock = threading.Lock()
        self.stages: list[dict] = []

    class _Stage:
        def __init__(self, report: "RunReport", name: str, client=None):
            self.report, self.name, self.client = report, name, client
            self._t0 = time.monotonic()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            dur = time.monotonic() - self._t0
            usage: dict = {}
            if self.client is not None:
                u = getattr(self.client, "last_usage", None) or {}
                usage = {
                    "model": u.get("model"),
                    "route": u.get("base_url"),
                    "prompt_messages": u.get("messages"),
                    "latency_s": u.get("latency_s"),
                    "call_ok": u.get("ok"),
                }
            rec = {
                "stage": self.name,
                "status": "error" if exc_type else "ok",
                "duration_s": round(dur, 3),
                **usage,
            }
            with self.report._lock:
                self.report.stages.append(rec)
            return False  # propagate exceptions

    def stage(self, name: str, client=None) -> "_Stage":
        return RunReport._Stage(self, name, client=client)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "schema": "hurcules.run-report",
                "schema_version": self.SCHEMA_VERSION,
                "run_id": self.run_id,
                "repo": self.repo,
                "started_at": self.started,
                "stages": list(self.stages),
                "total_duration_s": round(
                    sum(s.get("duration_s", 0.0) for s in self.stages), 3),
            }

    def save(self, dirpath) -> Path:
        d = Path(dirpath)
        d.mkdir(parents=True, exist_ok=True)
        safe = self.repo.replace("/", "__") or "repo"
        out = d / f"{self.run_id}__{safe}.json"
        out.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return out