"""TDD tests for HURCULES W2-[8] secrets-hygiene (scan + registry gate)."""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.secrets_hygiene import (
    HEXYL_CICD_FIXTURE_SHA256,
    MAX_FILE_SIZE,
    find_secret_values,
    regression_case_hexyl_cicd,
    scan_secrets,
    verify_no_values_in_package,
)

GH_TOKEN = "ghp_" + "A" * 36
SK_TOKEN = "sk-" + "a" * 32


def make_repo(tmp, files=None, subdirs=None) -> Path:
    """Small fixture repo; files = {rel_path: text}, subdirs = [rel_dir, ...]."""
    tmp = Path(tmp)
    repo = tmp / "repo"
    for d in subdirs or []:
        (repo / d).mkdir(parents=True, exist_ok=True)
    for rel, text in (files or {}).items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return repo


def json_blob(result) -> str:
    return json.dumps(result, sort_keys=True)


# --- fixture .env with API_KEY -> value pattern found, value never returned ---

def test_env_api_key_flagged_as_value_not_leaked():
    repo = make_repo(tempfile.mkdtemp(),
                     files={".env": f"API_KEY={SK_TOKEN}\n",
                            "README.md": "hello\n"})
    r = scan_secrets(str(repo))
    hits = {h["file"]: h["found"] for h in r["value_hits"]}
    assert ".env" in hits, "env api key must be a value hit"
    assert "openai-key" in hits[".env"]
    assert SK_TOKEN not in json_blob(r), "secret value leaked into scan output"


def test_scan_output_never_contains_values():
    repo = make_repo(tempfile.mkdtemp(), files={
        "creds.txt": f"api_key={SK_TOKEN}\nGITHUB={GH_TOKEN}\n",
        "aws.txt": "AKIA" + "0" * 16 + "\n"})
    r = scan_secrets(str(repo))
    blob = json_blob(r)
    for token in (SK_TOKEN, GH_TOKEN, "AKIA" + "0" * 16):
        assert token not in blob, f"value leaked: {token[:10]}..."


def test_aws_and_github_tokens_detected():
    repo = make_repo(tempfile.mkdtemp(), files={
        "gh.txt": f"token={GH_TOKEN}\n",
        "aws.txt": "key AKIA0123456789ABCDEF\n"})
    r = scan_secrets(str(repo))
    found = {h["file"]: h["found"] for h in r["value_hits"]}
    assert "github-token" in found["gh.txt"]
    assert "aws-access-key" in found["aws.txt"]


def test_slack_and_private_key_patterns():
    repo = make_repo(tempfile.mkdtemp(), files={
        "slack.txt": "xoxb-12345678901234567890\n",
        "key.pem": "-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n"})
    r = scan_secrets(str(repo))
    found = {h["file"]: h["found"] for h in r["value_hits"]}
    assert "slack-token" in found["slack.txt"]
    assert "private-key" in found["key.pem"]


def test_password_assignment_detected():
    repo = make_repo(tempfile.mkdtemp(), files={"app.conf": "password: hunter2\n"})
    r = scan_secrets(str(repo))
    found = {h["file"]: h["found"] for h in r["value_hits"]}
    assert "password-assignment" in found["app.conf"]


# --- regression: hexyl CICD yaml is a REFERENCE, never a leaked value -------

def test_hexyl_cicd_fixture_is_reference_not_value():
    repo = make_repo(tempfile.mkdtemp(), subdirs=[".github/workflows"], files={
        ".github/workflows/CICD.yml": regression_case_hexyl_cicd()})
    r = scan_secrets(str(repo))
    assert ".github/workflows/CICD.yml" in r["references"], \
        "CICD.yml must be flagged as a secret REFERENCE site"
    assert r["value_hits"] == [], \
        f"CICD.yml must not be a value leak, got {r['value_hits']}"


def test_hexyl_cicd_fixture_digest_stable():
    fx = regression_case_hexyl_cicd()
    assert "${{ secrets.GITHUB_TOKEN }}" in fx
    assert hashlib.sha256(fx.encode("utf-8")).hexdigest() == HEXYL_CICD_FIXTURE_SHA256


# --- verify_no_values_in_package gate --------------------------------------

def test_gate_passes_clean_package():
    pkg = {"schema": "hurcules.capability-package",
           "capabilities": [{"id": "hexdump", "name": "hex dump"}]}
    assert verify_no_values_in_package(pkg) is True


def test_gate_fails_package_embedding_token():
    pkg = {"capabilities": [{"name": "auth",
                             "note": f"login uses {SK_TOKEN}"}]}
    assert verify_no_values_in_package(pkg) is False


def test_gate_is_recursive_through_nested_struct():
    clean = {"a": {"b": [{"note": "plain"}, "text"]}}
    assert verify_no_values_in_package(clean) is True
    dirty = {"a": {"b": [{"note": f"aws {GH_TOKEN}"}]}}
    assert verify_no_values_in_package(dirty) is False
    # reference tokens are allowed — only VALUES trip the gate
    ref = {"capabilities": [{"name": "ci",
                             "env": "${{ secrets.GITHUB_TOKEN }}"}]}
    assert verify_no_values_in_package(ref) is True


# --- determinism & scan plumbing -------------------------------------------

def test_scan_is_deterministic():
    repo = make_repo(tempfile.mkdtemp(), files={
        ".env": f"API_KEY={SK_TOKEN}\n",
        "src/util.py": "import os\nos.system('ls')\n",
        ".github/workflows/ci.yml": regression_case_hexyl_cicd()})
    a = json_blob(scan_secrets(str(repo)))
    b = json_blob(scan_secrets(str(repo)))
    assert a == b, "secrets scan must be deterministic"


def test_size_cap_respected():
    repo = make_repo(tempfile.mkdtemp(), files={"small.txt": f"t={GH_TOKEN}\n"})
    r = scan_secrets(str(repo))
    assert "github-token" in find_secret_values(open(repo / "small.txt").read())
    # a file over the cap must NOT be scanned
    big = repo / "big.txt"
    big.write_text(f"token={GH_TOKEN}\n" + "#" * (MAX_FILE_SIZE + 1))
    r2 = scan_secrets(str(repo))
    assert all(h["file"] != "big.txt" for h in r2["value_hits"]), \
        "over-cap file must be skipped"


def test_skips_git_dir():
    repo = make_repo(tempfile.mkdtemp(), subdirs=[".git"],
                     files={".git/config": f"[credential] token={GH_TOKEN}\n",
                            "ok.txt": "hello\n"})
    r = scan_secrets(str(repo))
    assert all(h["file"] != ".git/config" for h in r["value_hits"]), \
        ".git must be skipped"


def test_secret_file_locations_reported():
    repo = make_repo(tempfile.mkdtemp(), files={
        ".env": "API_KEY=x\n", "id_rsa": "private\n", "readme.md": "hi\n"})
    r = scan_secrets(str(repo))
    assert ".env" in r["secret_file_locations"]
    assert "id_rsa" in r["secret_file_locations"]
    assert "readme.md" not in r["secret_file_locations"]


def test_references_reported_for_ci_yml():
    repo = make_repo(tempfile.mkdtemp(), files={
        ".github/workflows/ci.yml": "secret: ${{ secrets.DEPLOY_KEY }}\n"})
    r = scan_secrets(str(repo))
    assert ".github/workflows/ci.yml" in r["references"]


def test_raises_on_missing_dir():
    import pytest
    with pytest.raises(ValueError):
        scan_secrets("/definitely/not/here")