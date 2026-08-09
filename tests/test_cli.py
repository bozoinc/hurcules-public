"""Tests for the HURCULES CLI entry point (pyproject console script)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.cli import CLI_VERSION, main


def test_version_flag_prints_cli_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == CLI_VERSION


def test_cli_version_constant_matches_pyproject():
    assert CLI_VERSION == "0.7.0"


def test_no_args_prints_help_and_exits_zero(capsys):
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_ceiling_subcommand_is_honest_surface(capsys):
    # CLI surface only: not yet wired, exits 0, never crashes.
    assert main(["ceiling"]) == 0
    assert "not yet wired" in capsys.readouterr().out


def test_ingest_returns_1_when_repo_cannot_be_cloned(capsys):
    # No network / non-existent repo: clone fails -> pipeline reports
    # ok=False -> the CLI must exit 1 without crashing on argument errors.
    rc = main(["ingest", "--repo", "x/y"])
    assert rc == 1
    out = capsys.readouterr().out
    assert '"ok": false' in out  # the result dict is printed


def test_ingest_prints_result_dict(capsys):
    # Same code path as above but assert the report shape, not just the rc.
    main(["ingest", "--repo", "x/y"])
    out = capsys.readouterr().out
    assert '"repo": "x/y"' in out