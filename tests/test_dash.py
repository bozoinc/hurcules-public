"""TDD tests for Wave 4 localhost read-only dashboards (dash.py)."""
import json
import os
import sys
import tempfile
import threading
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.dash import (DASH_SECTIONS, collect, main, render_html, serve)  # noqa: E402

REGISTRY_DICT = {
    "e-approved": {
        "entry_id": "e-approved", "pkg_id": "owner/ok",
        "capability_count": 2, "status": "approved",
        "registered_at": "2026-08-01T00:00:00+00:00",
    },
    "e-candidate": {
        "entry_id": "e-candidate", "pkg_id": "owner/waiting",
        "capability_count": 1, "status": "candidate",
        "registered_at": "2026-08-02T00:00:00+00:00",
    },
}

REPORT = {
    "schema": "hurcules.run-report", "schema_version": 1,
    "run_id": "2026-08-03T00-00-00", "repo": "owner/repo",
    "started_at": "2026-08-03T00:00:00+00:00",
    "stages": [{"stage": "map", "status": "ok", "duration_s": 1.5}],
    "total_duration_s": 1.5,
}


def _write(tmpdir, relpath, payload):
    path = os.path.join(tmpdir, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(payload)
    return path


def test_collect_missing_files_returns_empty_sections():
    with tempfile.TemporaryDirectory() as td:
        data = collect(
            registry_path=os.path.join(td, "nope.json"),
            reports_dir=os.path.join(td, "no-reports"),
            ceiling_path=os.path.join(td, "no-ceiling.json"))
        assert set(data) == set(DASH_SECTIONS)
        for section in DASH_SECTIONS:
            assert data[section] == []


def test_collect_registry_populates_catalog_and_approvals():
    with tempfile.TemporaryDirectory() as td:
        reg = _write(td, "registry.json", json.dumps(REGISTRY_DICT))
        data = collect(registry_path=reg)
        assert [e["entry_id"] for e in data["catalog"]] == ["e-approved", "e-candidate"]
        assert [e["entry_id"] for e in data["approvals"]] == ["e-candidate"]
        assert data["catalog"][0]["capability_count"] == 2


def test_collect_accepts_list_shaped_registry():
    with tempfile.TemporaryDirectory() as td:
        reg = _write(td, "registry.json", json.dumps(list(REGISTRY_DICT.values())))
        data = collect(registry_path=reg)
        assert len(data["catalog"]) == 2
        assert len(data["approvals"]) == 1


def test_collect_spend_from_reports_dir():
    with tempfile.TemporaryDirectory() as td:
        r1 = dict(REPORT, run_id="b-run")
        r2 = dict(REPORT, run_id="a-run")
        _write(td, "reports/b.json", json.dumps(r1))
        _write(td, "reports/a.json", json.dumps(r2))
        data = collect(reports_dir=os.path.join(td, "reports"))
        assert [r["run_id"] for r in data["spend"]] == ["a-run", "b-run"]
        assert data["spend"][0]["total_duration_s"] == 1.5
        assert data["spend"][0]["repo"] == "owner/repo"


def test_collect_sandbox_is_honest_empty_placeholder():
    with tempfile.TemporaryDirectory() as td:
        data = collect(reports_dir=os.path.join(td, "empty"))
        assert data["sandbox"] == [], "no events system yet — must be []"


def test_collect_skips_corrupt_json_without_crashing():
    with tempfile.TemporaryDirectory() as td:
        _write(td, "registry.json", "{not valid json!!")
        _write(td, "reports/broken.json", "{{{")
        data = collect(registry_path=os.path.join(td, "registry.json"),
                       reports_dir=os.path.join(td, "reports"))
        assert data["catalog"] == [] and data["spend"] == []


def test_render_html_contains_all_sections():
    html = render_html({s: [] for s in DASH_SECTIONS})
    assert "<h1>HURCULES</h1>" in html
    for name in ("Catalog", "Spend ledger", "Approval queue", "Sandbox events"):
        assert f"<h2>{name}</h2>" in html


def test_render_html_escapes_hostile_data():
    hostile = [{"entry_id": "x", "pkg_id": "<script>alert(1)</script>",
                "status": "candidate", "registered_at": "t",
                "capability_count": 1}]
    html = render_html({"catalog": hostile, "spend": [], "approvals": hostile,
                        "sandbox": []})
    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html


def test_render_html_shows_key_fields():
    data = {"catalog": [{"pkg_id": "acme/cli", "status": "approved",
                         "capability_count": 3}],
            "spend": [{"run_id": "r-1", "total_duration_s": 2.5, "repo": "acme/cli"}],
            "approvals": [{"entry_id": "e-9", "registered_at": "2026-08-02T00:00:00"}],
            "sandbox": []}
    html = render_html(data)
    assert "acme/cli" in html and "approved" in html and "3" in html
    assert "r-1" in html and "2.5" in html
    assert "e-9" in html and "2026-08-02T00:00:00" in html


def test_serve_binds_localhost_on_ephemeral_port():
    server = serve(host="127.0.0.1", port=0)
    try:
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_address[1] > 0, "ephemeral port must be allocated"
    finally:
        server.server_close()


def test_serve_serves_rendered_html_at_root():
    with tempfile.TemporaryDirectory() as td:
        reg = _write(td, "registry.json", json.dumps(REGISTRY_DICT))
        server = serve(port=0, registry_path=reg)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/"
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = resp.read().decode("utf-8")
            assert resp.status == 200
            assert "<h1>HURCULES</h1>" in body
            assert "owner/waiting" in body  # real registry data served
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def test_main_help_returns_zero():
    assert main(["--help"]) == 0
