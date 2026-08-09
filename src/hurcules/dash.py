"""Wave 4 [18] — localhost-first read-only dashboards.

Four read-only views served from the repo (not SaaS): catalog (registry
entries), spend ledger (run-reports), approval queue (candidate entries),
sandbox events (placeholder — no event system yet). A minimal stdlib
http.server-based server renders simple HTML. Deterministic, no external
deps. Binds 127.0.0.1 by default (localhost-only, read-only).

Public seam:
    data = collect()                 # gather all sections into one dict
    html = render_html(data)         # self-contained HTML (no external assets)
    server = serve(port=8787)        # HTTPServer serving html at '/'
    main(["--port", "8787"])         # CLI entry point
"""

from __future__ import annotations

import argparse
import html
import http.server
import json
from pathlib import Path

DASH_SECTIONS = ["catalog", "spend", "approvals", "sandbox"]

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REGISTRY_PATH = ROOT / "data" / "registry" / "registry.json"
DEFAULT_REPORTS_DIR = ROOT / "data" / "run-reports"
DEFAULT_CEILING_PATH = ROOT / "data" / "ceiling-report.json"


def _read_json(path) -> object | None:
    """Read a JSON file; return None on any failure (missing/corrupt/unreadable)."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _registry_entries(raw) -> list:
    """Normalize registry.json to a list of entries.

    Registry persists a dict keyed by entry_id; accept a plain list too.
    """
    if isinstance(raw, dict):
        return list(raw.values())
    if isinstance(raw, list):
        return raw
    return []


def collect(registry_path=None, reports_dir=None, ceiling_path=None) -> dict:
    """Gather the four dashboard sections into one dict.

    registry_path: JSON file written by Registry (dict keyed by entry_id).
    reports_dir:   dir of run-report JSONs (schema hurcules.run-report).
    ceiling_path:  reserved for the ceiling-report view (not rendered yet).

    Never crashes on missing/unreadable files — absent sections are [].
    """
    entries = [e for e in _registry_entries(
        _read_json(registry_path or DEFAULT_REGISTRY_PATH)) if isinstance(e, dict)]
    entries.sort(key=lambda e: e.get("registered_at", ""))
    catalog = entries
    approvals = [e for e in catalog if e.get("status") == "candidate"]

    spend: list = []
    reports_dir = Path(reports_dir or DEFAULT_REPORTS_DIR)
    if reports_dir.is_dir():
        for report_file in sorted(reports_dir.glob("*.json")):
            raw = _read_json(report_file)
            if isinstance(raw, dict):
                spend.append(raw)
        spend.sort(key=lambda r: r.get("run_id", ""))

    return {
        "catalog": catalog,
        "spend": spend,
        "approvals": approvals,
        # Sandbox events do not exist yet — honest empty list, documented.
        "sandbox": [],
    }


def _esc(value) -> str:
    return html.escape(str(value))


def _render_table(headers, rows) -> str:
    """Minimal <table> for one section. Headers/rows must already be escaped."""
    if not rows:
        return "<p><em>(none)</em></p>"
    thead = "".join(f"<th>{h}</th>" for h in headers)
    tbody = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows)
    return f"<table border=\"1\"><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"


def render_html(data) -> str:
    """Self-contained HTML (no external CSS/JS) for the four sections.

    All data values are html.escaped — never inject raw data (hostile-by-default).
    """
    catalog = data.get("catalog", [])
    spend = data.get("spend", [])
    approvals = data.get("approvals", [])
    sandbox = data.get("sandbox", [])

    if sandbox:
        keys = sorted(sandbox[0].keys())
        sandbox_html = _render_table(
            keys, [[_esc(e.get(k)) for k in keys] for e in sandbox])
    else:
        sandbox_html = ("<p><em>No sandbox events yet — "
                        "event capture not implemented (honest empty list).</em></p>")

    sections = [
        ("Catalog", _render_table(
            ["pkg_id", "status", "capability_count"],
            [[_esc(e.get("pkg_id")), _esc(e.get("status")),
              _esc(e.get("capability_count"))] for e in catalog])),
        ("Spend ledger", _render_table(
            ["run_id", "total_duration_s", "repo"],
            [[_esc(r.get("run_id")), _esc(r.get("total_duration_s")),
              _esc(r.get("repo"))] for r in spend])),
        ("Approval queue", _render_table(
            ["entry_id", "registered_at"],
            [[_esc(a.get("entry_id")), _esc(a.get("registered_at"))]
             for a in approvals])),
        ("Sandbox events", sandbox_html),
    ]
    body = "\n".join(f"<h2>{name}</h2>\n{section_html}"
                     for name, section_html in sections)
    return ("<!DOCTYPE html>\n"
            "<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<title>HURCULES dashboard</title></head><body>\n"
            "<h1>HURCULES</h1>\n"
            + body
            + "\n</body></html>\n")


def _make_handler(collect_fn):
    """Handler class that serves render_html(collect_fn()) at '/' (read-only)."""
    class DashHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/":
                self.send_error(404, "not found")
                return
            body = render_html(collect_fn()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A002 — base signature
            pass

    return DashHandler


def serve(host="127.0.0.1", port=8787, registry_path=None,
          reports_dir=None, ceiling_path=None) -> http.server.HTTPServer:
    """Build (but do not run) a localhost read-only dashboard server.

    Data is re-collected on every request. Binds 127.0.0.1 by default so the
    dashboard is never exposed beyond this machine. Call server.serve_forever()
    (or hand the server to main()).
    """
    server = http.server.HTTPServer(
        (host, port),
        _make_handler(lambda: collect(registry_path, reports_dir, ceiling_path)))
    return server


def main(argv=None) -> int:
    """CLI entry point: parse flags, print the URL, serve until Ctrl-C."""
    parser = argparse.ArgumentParser(
        prog="hurcules-dash",
        description="Localhost read-only HURCULES dashboards "
                    "(catalog, spend, approvals, sandbox).")
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address (default: localhost only)")
    parser.add_argument("--port", type=int, default=8787,
                        help="bind port (default: 8787)")
    parser.add_argument("--registry", default=None,
                        help="path to registry.json "
                             "(default: data/registry/registry.json)")
    parser.add_argument("--reports", default=None,
                        help="dir of run-report JSONs (default: data/run-reports)")
    parser.add_argument("--ceiling", default=None,
                        help="path to ceiling-report.json (reserved; "
                             "default: data/ceiling-report.json)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help / bad args: argparse already printed
        return int(exc.code or 0)

    server = serve(host=args.host, port=args.port, registry_path=args.registry,
                   reports_dir=args.reports, ceiling_path=args.ceiling)
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"HURCULES dashboard (read-only): {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
