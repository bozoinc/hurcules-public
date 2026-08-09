"""TDD tests for Wave 2 [6] — capability-scoped sandbox profiles."""

import pytest

from hurcules.sandbox import SandboxLimits
from hurcules.profiles import (
    apply_network_args, network_for, profile_for, profile_name_for,
)


def test_default_readonly_no_network():
    limits = profile_for("TOOL", ["filesystem_read_only"])
    assert limits.cpus == 0.5
    assert limits.memory == "256m"
    assert network_for("TOOL", ["filesystem_read_only"]) is False


def test_none_permission_is_tightest():
    limits = profile_for("TOOL", ["none"])
    assert limits.cpus == 0.25
    assert limits.memory == "128m"
    assert limits.pids == 32
    assert network_for("TOOL", ["none"]) is False


def test_network_permission_grants_network():
    limits = profile_for("TOOL", ["network"])
    assert limits.memory == "512m"
    assert limits.cpus == 1.0
    assert network_for("TOOL", ["network"]) is True


def test_shell_profile():
    limits = profile_for("WORKFLOW", ["shell"])
    assert limits.memory == "1g"
    assert limits.pids == 256
    assert network_for("WORKFLOW", ["shell"]) is True


def test_readwrite_profile():
    limits = profile_for("TOOL", ["filesystem_read_write"])
    assert limits.memory == "512m"
    assert network_for("TOOL", ["filesystem_read_write"]) is False


def test_base_overlay_preserves_max_output():
    base = SandboxLimits(max_output=500_000)
    limits = profile_for("TOOL", ["readonly"], base=base)
    assert limits.max_output == 500_000
    assert limits.memory == "256m"  # profile value wins over base default


def test_profile_names():
    assert profile_name_for("x", []) == "readonly"
    assert profile_name_for("x", ["network"]) == "network"
    assert profile_name_for("x", ["shell"]) == "shell"
    assert profile_name_for("x", ["none"]) == "none"
    assert profile_name_for("x", ["filesystem_read_write"]) == "readwrite"


def test_apply_network_args():
    assert apply_network_args(["filesystem_read_only"]) == ["--network", "none"]
    assert apply_network_args(["network"]) == ["--network", "bridge"]
    assert apply_network_args(["shell"]) == ["--network", "bridge"]
    assert apply_network_args(["none"]) == ["--network", "none"]


def test_most_permissive_permission_wins():
    # network + readwrite together -> network wins (never less than earned)
    limits = profile_for("TOOL", ["network", "filesystem_read_write"])
    assert network_for("TOOL", ["network", "filesystem_read_write"]) is True
    assert limits.cpus == 1.0


def test_deterministic():
    a = profile_for("TOOL", ["network", "filesystem_read_write"])
    b = profile_for("TOOL", ["network", "filesystem_read_write"])
    assert a == b  # frozen dataclass equality -> same policy every call


def test_returns_frozen_sandboxlimits():
    limits = profile_for("TOOL", ["network"])
    assert isinstance(limits, SandboxLimits)
    with pytest.raises(Exception):
        limits.cpus = 3.0  # frozen dataclass -> cannot mutate


def test_limits_carry_network_flag():
    # the returned SandboxLimits object must encode the network decision so
    # Sandbox.run() honors it via docker_args() — no separate wiring needed
    assert profile_for("TOOL", ["network"]).network is True
    assert profile_for("TOOL", ["filesystem_read_only"]).network is False
    assert profile_for("TOOL", ["none"]).network is False
    assert profile_for("WORKFLOW", ["shell"]).network is True


def test_docker_args_include_network():
    no_net = profile_for("TOOL", ["filesystem_read_only"]).docker_args()
    assert "--network" in no_net and "none" in no_net
    yes_net = profile_for("TOOL", ["network"]).docker_args()
    assert "--network" in yes_net and "bridge" in yes_net