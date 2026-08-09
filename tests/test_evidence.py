"""TDD tests for the evidence-validity checker (deterministic, NO LLM).

Covers W1-[4]: verify every claimed evidence file+scope actually exists in the
repo and the scope text appears in the file content at the pinned repo path.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.evidence import verify_evidence, verify_package


def _make_repo(tmp_path):
    """Create a tiny fake repo: two files with known content."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "def parse_config(path):\n"
        "    # DAG execution runtime lives here\n"
        "    return path\n"
    )
    (tmp_path / "README.md").write_text(
        "HURCULES is a repository compiler.\n"
    )
    return tmp_path


def _cap(cid="c1", file="src/main.py", scope="DAG execution runtime"):
    return {
        "id": cid, "name": "x", "ontology_type": "TOOL",
        "evidence": [{"file": file, "scope": scope}],
        "confidence": 0.9, "requirements": [],
    }


# --- verify_evidence ---------------------------------------------------------


def test_pass_when_file_and_scope_present(tmp_path):
    repo = _make_repo(tmp_path)
    r = verify_evidence([_cap(scope="DAG execution runtime")], repo)
    res = r["c1"]
    assert res["status"] == "PASS"
    assert res["missing_files"] == []
    assert res["scope_missing"] == []


def test_scope_match_is_case_insensitive(tmp_path):
    # Scope text in file is uppercase; claim uses lowercase.
    repo = _make_repo(tmp_path)
    r = verify_evidence([_cap(scope="dag execution RUNTIME")], repo)
    assert r["c1"]["status"] == "PASS"


def test_fail_when_file_missing(tmp_path):
    repo = _make_repo(tmp_path)
    r = verify_evidence([_cap(file="not/here.py", scope="anything")], repo)
    res = r["c1"]
    assert res["status"] == "FAIL"
    assert res["missing_files"] == ["not/here.py"]
    assert res["scope_missing"] == []


def test_fail_when_scope_not_found(tmp_path):
    repo = _make_repo(tmp_path)
    r = verify_evidence([_cap(scope="quantum teleportation")], repo)
    res = r["c1"]
    assert res["status"] == "FAIL"
    assert res["missing_files"] == []
    assert res["scope_missing"] == ["src/main.py"]


def test_fail_when_scope_empty(tmp_path):
    # Evidence entry without a scope is not verifiable -> FAIL.
    repo = _make_repo(tmp_path)
    r = verify_evidence([_cap(scope="")], repo)
    assert r["c1"]["status"] == "FAIL"
    assert r["c1"]["scope_missing"] == ["src/main.py"]


def test_multi_evidence_partial_failure_tracked(tmp_path):
    # One good entry + one scope-missing entry -> FAIL, but both lists precise.
    repo = _make_repo(tmp_path)
    cap = {
        "id": "c1", "name": "x", "ontology_type": "TOOL",
        "evidence": [
            {"file": "src/main.py", "scope": "DAG execution runtime"},
            {"file": "README.md", "scope": "galactic empire"},
        ],
        "confidence": 0.9, "requirements": [],
    }
    res = verify_evidence([cap], repo)["c1"]
    assert res["status"] == "FAIL"
    assert res["missing_files"] == []
    assert res["scope_missing"] == ["README.md"]


def test_accepts_full_package_dict(tmp_path):
    repo = _make_repo(tmp_path)
    package = {
        "schema": "hurcules.capability-package-v1",
        "capabilities": [_cap()],
    }
    r = verify_evidence(package, repo)
    assert r["c1"]["status"] == "PASS"


def test_no_evidence_fails(tmp_path):
    repo = _make_repo(tmp_path)
    cap = {"id": "c1", "name": "x", "ontology_type": "TOOL",
           "evidence": [], "confidence": 0.9, "requirements": []}
    assert verify_evidence([cap], repo)["c1"]["status"] == "FAIL"


def test_binary_file_scope_lookup_does_not_crash(tmp_path):
    repo = _make_repo(tmp_path)
    (repo / "blob.bin").write_bytes(b"\x00\xff\x01\xde\xad\xbe\xef")
    r = verify_evidence([_cap(file="blob.bin", scope="anything")], repo)
    assert r["c1"]["status"] == "FAIL"
    assert r["c1"]["scope_missing"] == ["blob.bin"]


def test_verify_evidence_deterministic(tmp_path):
    repo = _make_repo(tmp_path)
    caps = [
        _cap(cid="c1", scope="DAG execution runtime"),
        _cap(cid="c2", file="ghost.py", scope="anything"),
        _cap(cid="c3", scope="not here"),
    ]
    a = json.dumps(verify_evidence(caps, repo), sort_keys=True)
    b = json.dumps(verify_evidence(caps, repo), sort_keys=True)
    assert a == b


# --- verify_package ----------------------------------------------------------


def test_verify_package_ok(tmp_path):
    repo = _make_repo(tmp_path)
    package = {"capabilities": [_cap()]}
    r = verify_package(package, repo)
    assert r["ok"] is True
    assert r["results"]["c1"]["status"] == "PASS"


def test_verify_package_not_ok(tmp_path):
    repo = _make_repo(tmp_path)
    package = {"capabilities": [_cap(file="ghost.py", scope="x")]}
    r = verify_package(package, repo)
    assert r["ok"] is False
    assert r["results"]["c1"]["status"] == "FAIL"


def test_verify_package_empty_is_ok(tmp_path):
    repo = _make_repo(tmp_path)
    r = verify_package({"capabilities": []}, repo)
    assert r["ok"] is True
    assert r["results"] == {}


def test_verify_package_deterministic(tmp_path):
    repo = _make_repo(tmp_path)
    package = {"capabilities": [_cap(), _cap(cid="c2", file="ghost.py")]}
    a = json.dumps(verify_package(package, repo), sort_keys=True)
    b = json.dumps(verify_package(package, repo), sort_keys=True)
    assert a == b