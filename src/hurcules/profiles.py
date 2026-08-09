"""HURCULES Wave 2 [6] — capability-scoped sandbox profiles.

Today one global SandboxLimits applies to every execution. Enterprises need
least-privilege PER CAPABILITY: map a capability's ontology_type + requested
permissions to a resource/network policy profile, then layer it onto a
SandboxLimits so each capability digs its own hole (no network unless it asked
for network, tighter limits unless it earned more).

Public seam:
  profile_for(ontology_type, permissions, base=None) -> SandboxLimits
  network_for(ontology_type, permissions) -> bool
  apply_network_args(profile_name) -> list[str]  # ['--network','none'|'bridge']

Deterministic, stdlib only, no sandbox.py modification (it reuses the frozen
SandboxLimits dataclass shape: cpus/memory/memory_swap/pids/timeout_s/max_output).
"""

from __future__ import annotations

from hurcules.sandbox import SandboxLimits  # reuse the frozen dataclass shape

# Named profile -> (SandboxLimits overrides, network_enabled)
_PROFILES: dict[str, tuple[SandboxLimits, bool]] = {
    # tightest: analysis-grade, no network, minimal resources
    "none": (SandboxLimits(cpus=0.25, memory="128m", memory_swap="128m",
                           pids=32, timeout_s=30), False),
    # read-only capability surface: default; no network
    "readonly": (SandboxLimits(cpus=0.5, memory="256m", memory_swap="256m",
                               pids=64, timeout_s=30), False),
    # read-write capability surface (writes inside the disposable FS); no network
    "readwrite": (SandboxLimits(cpus=0.5, memory="512m", memory_swap="512m",
                                pids=64, timeout_s=60), False),
    # network access earned by a capability that explicitly requested it
    "network": (SandboxLimits(cpus=1.0, memory="512m", memory_swap="512m",
                              pids=128, timeout_s=120), True),
    # shell execution (most privileged): network + more headroom
    "shell": (SandboxLimits(cpus=1.0, memory="1g", memory_swap="1g",
                            pids=256, timeout_s=180), True),
}


def profile_for(ontology_type: str,
                permissions: list[str] | None = None,
                base: SandboxLimits | None = None) -> SandboxLimits:
    """Choose a sandbox profile for a capability and return concrete limits.

    Rules (most permissive wins, so a capability never gets less than it
    earned, but never more than the profile grants):
      1. 'none' permission  -> 'none' profile (tightest)
      2. 'shell'            -> 'shell'
      3. 'network'          -> 'network'
      4. 'filesystem_read_write' -> 'readwrite'
      5. else               -> 'readonly' (default)
    `base` overlays the chosen profile onto non-default limits (used to scale
    by capability size when desired); when base is None the profile defaults
    apply directly.
    """
    perms = set(permissions or [])
    if "none" in perms:
        name = "none"
    elif "shell" in perms:
        name = "shell"
    elif "network" in perms:
        name = "network"
    elif "filesystem_read_write" in perms:
        name = "readwrite"
    else:
        name = "readonly"

    prof_limits, prof_network = _PROFILES[name]
    if base is None:
        return SandboxLimits(
            cpus=prof_limits.cpus, memory=prof_limits.memory,
            memory_swap=prof_limits.memory_swap, pids=prof_limits.pids,
            timeout_s=prof_limits.timeout_s,
            max_output=prof_limits.max_output,
            network=prof_network,
        )
    # overlay: start from the caller's base, take profile values where set
    return SandboxLimits(
        cpus=prof_limits.cpus,
        memory=prof_limits.memory,
        memory_swap=prof_limits.memory_swap,
        pids=prof_limits.pids,
        timeout_s=prof_limits.timeout_s,
        max_output=base.max_output,
        network=prof_network,
    )


def network_for(ontology_type: str,
                permissions: list[str] | None = None) -> bool:
    """Does this capability get network access? Mirrors profile_for's rules."""
    perms = set(permissions or [])
    if "none" in perms:
        return False
    if "shell" in perms or "network" in perms:
        return True
    return False


def profile_name_for(ontology_type: str,
                     permissions: list[str] | None = None) -> str:
    """Return the profile name (none/readonly/readwrite/network/shell)."""
    perms = set(permissions or [])
    if "none" in perms:
        return "none"
    if "shell" in perms:
        return "shell"
    if "network" in perms:
        return "network"
    if "filesystem_read_write" in perms:
        return "readwrite"
    return "readonly"


def apply_network_args(permissions: list[str] | None = None) -> list[str]:
    """Docker args that scope the network: ['--network','none'|'bridge']."""
    mode = "bridge" if network_for("", permissions) else "none"
    return ["--network", mode]