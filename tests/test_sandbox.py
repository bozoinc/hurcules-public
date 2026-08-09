"""TDD tests for Stage 7 sandboxed execution.

Covers: sandbox availability, hard-isolation flags used at run time (env
scrub, network none, read-only mount, cap-drop, pids/mem/cpu limits, timeout),
the opt-in execution gate (never default), and the hostile-containment exit
gate (synthetic escape attempts run harmlessly inside the container).

Docker is required. Tests that genuinely spawn containers are skipped when
`docker info` fails so the suite runs in CI without a daemon.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.sandbox import Sandbox, SandboxLimits, SandboxUnavailable
from hurcules.adapter import compose_agent, can_execute


def _docker_ok() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=15)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


REQUIRES_DOCKER = pytest.mark.skipif(not _docker_ok(), reason="docker daemon unavailable")


# ---------------------------------------------------------------------------
# Sandbox construction / policy (no container spawn)
# ---------------------------------------------------------------------------


def test_limits_carry_docker_flags():
    lim = SandboxLimits(cpus=0.25, memory="128m", pids=16)
    args = lim.docker_args()
    assert "--cpus" in args and "0.25" in args
    assert "--memory" in args and "128m" in args
    assert "--pids-limit" in args and "16" in args


def test_sandbox_requires_docker_cli(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(SandboxUnavailable):
        Sandbox()


# ---------------------------------------------------------------------------
# Execution gate: opt-in, never default
# ---------------------------------------------------------------------------


def test_execution_denied_without_sandbox():
    spec = {"ok": True, "composed_from": [{"name": "x", "ontology_type": "TOOL"}]}
    # no approved-execution flag and no sandbox
    decision = can_execute(spec, approved=False, sandbox_available=False)
    assert decision["execute"] is False
    assert decision["reason"] != "execution_approved"


def test_execution_requires_approval():
    spec = {"ok": True, "composed_from": [{"name": "x", "ontology_type": "TOOL"}]}
    # sandbox present but capability not approved -> still deny
    assert can_execute(spec, approved=False, sandbox_available=True)["execute"] is False


def test_execution_requires_sandbox_even_if_approved():
    spec = {"ok": True, "composed_from": [{"name": "x", "ontology_type": "TOOL"}]}
    # approved but no real sandbox -> deny (boundary is a system property)
    assert can_execute(spec, approved=True, sandbox_available=False)["execute"] is False


def test_execution_approved_only_when_approved_and_sandboxed():
    spec = {"ok": True, "composed_from": [{"name": "x", "ontology_type": "TOOL"}]}
    d = can_execute(spec, approved=True, sandbox_available=True)
    assert d["execute"] is True
    assert "sandbox" in d["method"]


# ---------------------------------------------------------------------------
# Containment — spawn a container (needs docker)
# ---------------------------------------------------------------------------


@REQUIRES_DOCKER
def test_benign_command_runs_in_sandbox():
    s = Sandbox(limits=SandboxLimits(timeout_s=20))
    r = s.run("echo SANDBOX_HELLO")
    assert r.ok
    assert "SANDBOX_HELLO" in r.stdout


@REQUIRES_DOCKER
def test_env_scrubbed_no_host_secrets():
    os.environ["HURCULES_HOST_SECRET"] = "topsecret"
    s = Sandbox(limits=SandboxLimits(timeout_s=20))
    try:
        r = s.run("echo \"[${HURCULES_HOST_SECRET}]\"")
        assert "topsecret" not in r.stdout
        assert "[]" in r.stdout  # var unset inside container
    finally:
        del os.environ["HURCULES_HOST_SECRET"]


@REQUIRES_DOCKER
def test_network_denied():
    s = Sandbox(limits=SandboxLimits(timeout_s=25))
    r = s.run("wget -q -T 3 http://example.com && echo NET_OK || echo NET_DENIED")
    assert "NET_DENIED" in r.stdout or "NET_DENIED" in r.stderr or "bad address" in r.stderr


@REQUIRES_DOCKER
def test_hostile_attempts_cannot_touch_host():
    """Exit-gate: synthetic escape attempts stay contained; host untouched."""
    host_probe = os.path.join(tempfile.gettempdir(), "hurcules-hostile-marker")
    if os.path.exists(host_probe):
        os.remove(host_probe)

    hostile = (
        # try to write a marker into host's temp dir (mount of /tmp is the container's, not host's)
        "touch /tmp/hurcules-hostile-marker; "
        # try to read host-only paths (should simply not exist / be denied)
        "cat /etc/hostname 2>/dev/null | head -1; "           # container hostname, harmless
        "ls /home/user 2>/dev/null; "                          # host home, absent
        "ls /mnt/c 2>/dev/null; "                             # Windows mount, absent
        "cat /root/.ssh/id_rsa 2>/dev/null; "                 # ssh key, absent
        "env | grep -i SECRET 2>/dev/null; "                  # no secrets
        "echo DONE"
    )
    s = Sandbox(limits=SandboxLimits(timeout_s=20))
    r = s.run(hostile)

    # the workload must be contained: it cannot reach host paths or secrets
    assert "id_rsa" not in r.stdout
    assert "/mnt/c" not in r.stdout
    # the host marker in OUR /tmp (not container's) must NOT be created
    assert os.path.exists(host_probe) is False


@REQUIRES_DOCKER
def test_truth_told_first___hostile_probe_with_mount_stays_readonly():
    """A repo mounted read-only cannot be mutated by the sandboxed workload."""
    with tempfile.TemporaryDirectory() as repo:
        p = Path(repo) / "content.txt"
        p.write_text("canary")
        s = Sandbox(limits=SandboxLimits(timeout_s=20))
        r = s.run(f"echo 'pwned' > {repo}/content.txt; cat {repo}/content.txt",
                  mount_host=repo)
        # read-only mount: write fails, canary intact (assert inside the tmpdir ctx)
        assert os.path.exists(p), "repo file vanished"
        assert p.read_text() == "canary", "repo file mutated through read-only mount"


def test_execution_never_default_when_spec_lacks_approval_flags():
    """Defense-in-depth: even malformed spec cannot auto-authorize execution."""
    d = can_execute({"ok": True, "composed_from": []},
                    approved=False, sandbox_available=True)
    assert d["execute"] is False