"""TDD tests for Wave 0 [14] — cost & duration ledger."""

import json
import time
from pathlib import Path

from hurcules.ledger import RunReport, attach_usage


def _fake_chat(messages, delay=0.03):
    time.sleep(delay)
    return '{"ok": true}'


def test_run_report_records_stage_duration():
    rpt = RunReport(repo="owner/repo")
    with rpt.stage("map"):
        time.sleep(0.02)
    with rpt.stage("analyst"):
        time.sleep(0.03)
    stages = rpt.to_dict()["stages"]
    assert [s["stage"] for s in stages] == ["map", "analyst"]
    assert all(s["status"] == "ok" for s in stages)
    assert all(s["duration_s"] >= 0.0 for s in stages)
    assert stages[1]["duration_s"] > stages[0]["duration_s"]


def test_run_report_records_usage_from_client():
    client = attach_usage(_fake_chat, model="m1", base_url="http://r/v1")
    rpt = RunReport(repo="o/r")
    with rpt.stage("analyst", client):
        client([{"role": "user", "content": "x"}])
    rec = rpt.to_dict()["stages"][0]
    assert rec["model"] == "m1"
    assert rec["route"] == "http://r/v1"
    assert rec["prompt_messages"] == 1
    assert rec["latency_s"] > 0.0
    assert rec["call_ok"] is True


def test_stage_error_marked_not_crashing():
    rpt = RunReport(repo="o/r")
    try:
        with rpt.stage("bomb"):
            raise ValueError("boom")
    except ValueError:
        pass
    rec = rpt.to_dict()["stages"][0]
    assert rec["status"] == "error"


def test_attach_usage_is_idempotent():
    c1 = attach_usage(_fake_chat, "m", "u")
    c2 = attach_usage(c1, "m", "u")  # second wrap must not double-wrap
    assert c1 is c2


def test_usage_live_updates_per_call():
    client = attach_usage(_fake_chat, "m", "u")
    client([{"role": "user"}])
    first = client.last_usage["messages"]
    client([{"role": "user"}, {"role": "user"}])
    assert client.last_usage["messages"] == 2
    assert first == 1


def test_usage_reflects_messages_when_no_provider_tokens():
    # Provider seam returns content only, so tokens default absent; the report
    # must still serialise cleanly and never fabricate token counts.
    client = attach_usage(_fake_chat, "m", "u")
    client([{"role": "user", "content": "hi"}])
    u = client.last_usage
    assert "prompt_tokens" not in u  # honest: we do not have them yet


def test_to_dict_shape():
    d = RunReport(repo="o/r").to_dict()
    assert d["schema"] == "hurcules.run-report"
    assert d["schema_version"] == 1
    assert d["stages"] == []
    assert d["total_duration_s"] == 0.0


def test_save_writes_parsable_json(tmp_path: Path):
    rpt = RunReport(repo="owner/name", run_id="20260809-000000")
    with rpt.stage("map"):
        pass
    out = rpt.save(tmp_path)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["repo"] == "owner/name"
    assert data["stages"][0]["stage"] == "map"
    assert "20260809-000000" in out.name


def test_run_id_defaults_to_timestamp():
    rpt = RunReport(repo="o/r")
    assert "T" in rpt.run_id  # ISO timestamp (colons replaced is fine)