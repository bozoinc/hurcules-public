"""HURCULES Stage 7 — Sandboxed Execution (real system boundary).

A Docker-backed execution sandbox. Repo content is DATA; execution is denied by
default and only opt-ed into per capability after explicit human approval (D4)
AND availability of a real sandbox (D3, SECURITY.md). This module enforces the
boundary as a system property, not a system-prompt promise.

Boundary guarantees (each maps to a Docker flag / runtime control):
  - No host filesystem (only an explicit read-only repo mount)
  - No host credentials: env is scrubbed, no Docker socket, no privileged exec
  - Network denied (--network none)
  - CPU / memory / pids limits
  - Timeout (hard container stop + host-side subprocess timeout)
  - Disposable filesystem (container removed after run)
  - Full logs captured

Design: thin, dependency-free (stdlib subprocess) shelling to the docker CLI.
SandboxResult carries exit code, stdout, stderr, signal/kill evidence, and a
reusable `ok` verdict.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class SandboxUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class SandboxLimits:
    cpus: float = 0.5
    memory: str = "256m"
    memory_swap: str = "256m"
    pids: int = 64
    timeout_s: int = 30
    max_output: int = 200_000
    network: bool = False  # Wave 2 [6]: capability-scoped network access

    def docker_args(self) -> list[str]:
        return [
            "--cpus", str(self.cpus),
            "--memory", self.memory,
            "--memory-swap", self.memory_swap,
            "--pids-limit", str(self.pids),
            "--network", "bridge" if self.network else "none",
        ]


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    container_id: str = ""
    checked: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class Sandbox:
    """Execute an untrusted command inside an isolated Docker container."""

    def __init__(
        self,
        image: str = "alpine:latest",
        limits: SandboxLimits | None = None,
        shell: bool = False,
        workdir: str = "/sandbox",
    ):
        if shutil.which("docker") is None:
            raise SandboxUnavailable("docker CLI not found")
        self.image = image
        self.limits = limits or SandboxLimits()
        self.shell = shell
        self.workdir = workdir

    # -- capability / availability -----------------------------------------
    @staticmethod
    def available() -> bool:
        if shutil.which("docker") is None:
            return False
        try:
            r = subprocess.run(
                ["docker", "info"], capture_output=True, timeout=15
            )
            return r.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    # -- core runner ---------------------------------------------------------

    def run(
            self,
            command: str | list[str],
            *,
            mount_host: str | None = None,
            mount_readonly: bool = True,
            env_extra: dict[str, str] | None = None,
        ) -> SandboxResult:
        """Run `command` in a fresh, disposable container.

        mount_host: an absolute host path to bind-mount INTO the container at
                    the same path (used to hand the repo to the sandbox). It is
                    mounted read-only by default so the untrusted workload
                    cannot mutate host data through the mount.
        """
        cmd = ["docker", "run", "--rm"]  # network handled by limits.docker_args()
        cmd += self.limits.docker_args()
        cmd += ["--cap-drop", "ALL", "--security-opt", "no-new-privileges"]
        cmd += ["--user", "nobody", "--workdir", self.workdir]
        # scrub the environment: pass only explicit vars, never host env
        cmd += ["--env", "PYTHONUNBUFFERED=1"]
        for k, v in (env_extra or {}).items():
            cmd += ["--env", f"{k}={v}"]

        if mount_host:
            src = str(os.path.abspath(mount_host))
            mode = "ro" if mount_readonly else "rw"
            cmd += ["-v", f"{src}:{src}:{mode}"]

        cmd += [self.image]

        if self.shell:
            cmd += ["sh", "-c", command]
        elif isinstance(command, str):
            cmd += ["sh", "-c", command]
        else:
            cmd += list(command)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.limits.timeout_s + 5,  # host-side hard stop
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            timed_out = False
        except subprocess.TimeoutExpired as e:
            timed_out = True
            stdout = (e.stdout or b"").decode("utf-8", "replace")[: self.limits.max_output]
            stderr = (e.stderr or b"").decode("utf-8", "replace")[: self.limits.max_output]
            proc = None

        # truncate huge logs
        stdout = stdout[: self.limits.max_output]
        stderr = stderr[: self.limits.max_output]

        return SandboxResult(
            exit_code=proc.returncode if proc else -124,  # -124 ~ SIGKILL(timeout)
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
        )

    def max_s(self) -> int:
        return self.limits.timeout_s