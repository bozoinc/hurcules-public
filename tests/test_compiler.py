"""TDD tests for Stage 4 capability compiler (deterministic validator)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.compiler import compile_package

MAP = {
    "repository": "/fake/repo",
    "file_count": 3,
    "file_tree": ["src/main.py", "src/util.py", "README.md"],
    "languages": {"python": 2, "markdown": 1},
    "dependency_manifests": ["pyproject.toml"],
    "entry_points": ["src/main.py"],
    "test_files": [],
    "documentation_files": ["README.md"],
    "secret_file_locations": [],
    "risk_flags": [],
}

VALID = {"capabilities": [{
    "id": "c1", "name": "JSON parser", "ontology_type": "TOOL",
    "evidence": [{"file": "src/main.py", "scope": "parse"}],
    "confidence": 0.9, "requirements": [],
}]}


def test_ok_valid_package():
    res = compile_package(VALID, MAP, "/fake/repo")
    assert res["ok"] is True, res["errors"]
    assert res["errors"] == []
    pkg = res["package"]
    assert pkg["schema"] == "hurcules.capability-package-v1"
    assert pkg["registry"]["status"] == "candidate"  # never auto-approved (D3)
    assert pkg["security"]["hostile_by_default"] is True
    assert pkg["security"]["execution_denied_by_default"] is True


def test_rejects_evidence_for_missing_file():
    bad = {"capabilities": [{
        "id": "c1", "name": "Ghost", "ontology_type": "TOOL",
        "evidence": [{"file": "not/here.py", "scope": "x"}],
        "confidence": 0.9, "requirements": [],
    }]}
    res = compile_package(bad, MAP, "/fake/repo")
    assert res["ok"] is False
    assert any("not/here.py" in e for e in res["errors"])


def test_rejects_duplicate_ids():
    bad = {"capabilities": [
        {"id": "c1", "name": "A", "ontology_type": "TOOL",
         "evidence": [{"file": "src/main.py", "scope": "x"}], "confidence": 0.9, "requirements": []},
        {"id": "c1", "name": "B", "ontology_type": "TOOL",
         "evidence": [{"file": "src/util.py", "scope": "y"}], "confidence": 0.9, "requirements": []},
    ]}
    res = compile_package(bad, MAP, "/fake/repo")
    assert res["ok"] is False
    assert any("duplicate" in e for e in res["errors"])


def test_rejects_bad_ontology():
    bad = {"capabilities": [{
        "id": "c1", "name": "x", "ontology_type": "MAGIC",
        "evidence": [{"file": "src/main.py", "scope": "x"}],
        "confidence": 0.9, "requirements": [],
    }]}
    res = compile_package(bad, MAP, "/fake/repo")
    assert res["ok"] is False
    assert any("ontology" in e for e in res["errors"])


def test_compile_is_deterministic():
    a = json.dumps(compile_package(VALID, MAP, "/fake/repo"), sort_keys=True)
    b = json.dumps(compile_package(VALID, MAP, "/fake/repo"), sort_keys=True)
    assert a == b


def test_package_includes_provenance_and_security():
    res = compile_package(VALID, MAP, "/fake/repo")
    pkg = res["package"]
    assert pkg["provenance"]["repository"] == "/fake/repo"
    assert "security" in pkg
    assert pkg["security"]["secret_file_locations"] == []


def test_requirements_carried_through():
    with_req = {"capabilities": [{
        "id": "c1", "name": "x", "ontology_type": "WORKFLOW",
        "evidence": [{"file": "src/main.py", "scope": "x"}],
        "confidence": 0.8, "requirements": ["python", "flask"],
    }]}
    res = compile_package(with_req, MAP, "/fake/repo")
    assert res["package"]["capabilities"][0]["requirements"] == ["python", "flask"]


def test_rejects_inconclusive_analysis():
    # W1-[1] quality floor: an INCONCLUSIVE analysis is never compiled into a
    # valid empty package (the pilot's silent-empty failure mode).
    inconclusive = {"capabilities": [], "conclusion": "inconclusive"}
    res = compile_package(inconclusive, MAP, "/fake/repo")
    assert res["ok"] is False
    assert any("inconclusive" in e for e in res["errors"])