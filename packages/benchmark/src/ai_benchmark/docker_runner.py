"""Isolated execution (§9). Separate agent/evaluator invocations, hardened flags."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from ai_core.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class ContainerResult:
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool


@dataclass(frozen=True, slots=True)
class Mount:
    source: Path
    target: str
    read_only: bool = True


@dataclass(frozen=True, slots=True)
class ExecutionSpec:
    command: list[str]
    workdir: Path
    timeout_seconds: float
    mounts: tuple[Mount, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    cpu_limit: float = 2.0
    memory_limit: str = "4g"
    pids_limit: int = 256
    container_user: str = "10001:10001"
    network_enabled: bool = False
    image: str = "python:3.12-slim"


def docker_available() -> bool:
    """Return True when the `docker` CLI exists and a test container runs."""
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            [  # noqa: S607 - intentional PATH lookup of explicit tool
                "docker",
                "info",
                "--format",
                "{{.ServerVersion}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _forbidden_mount(source: Path) -> bool:
    text = str(source.resolve(strict=False))
    if text in ("/", "/root", "/home") or text == "/var/run/docker.sock":
        return True
    if "docker.sock" in text:
        return True
    home = str(Path.home().resolve(strict=False))
    # Never mount the whole home or credential dirs wholesale.
    if text == home:
        return True
    for sensitive in (".config", ".docker", ".claude", ".agy", ".aws", ".ssh"):
        if text == f"{home}/{sensitive}" or text.endswith(f"/{sensitive}"):
            return True
    return False


def docker_args(spec: ExecutionSpec, *, name: str) -> list[str]:
    """Build a hardened `docker run` argument list (no shell)."""
    if not spec.command:
        raise ConfigurationError("empty container command")
    for mount in spec.mounts:
        if _forbidden_mount(mount.source):
            raise ConfigurationError(f"refused unsafe mount: {mount.source}")
    args: list[str] = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        f"--cpus={spec.cpu_limit}",
        "--memory",
        spec.memory_limit,
        "--pids-limit",
        str(spec.pids_limit),
        "--user",
        spec.container_user,
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--network",
        "bridge" if spec.network_enabled else "none",
        "--workdir",
        "/workspace",
    ]
    # Read-only rootfs with writable tmp.
    args += [
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=256m",  # noqa: S108 - docker tmpfs mount, not a tempfile
    ]
    for mount in spec.mounts:
        mode = "ro" if mount.read_only else "rw"
        args += ["--volume", f"{mount.source}:{mount.target}:{mode}"]
    for key, value in spec.env.items():
        args += ["--env", f"{key}={value}"]
    args.append(spec.image)
    args.extend(spec.command)
    return args


def run_local(spec: ExecutionSpec) -> ContainerResult:
    """Run *spec.command* directly in *spec.workdir* (tests / no-docker fallback).

    Uses an argument list, bounded timeout, and an explicit env that preserves
    ``PATH`` (so the active venv's executables resolve) plus ``spec.env``.
    Secrets are never injected here; callers pass only explicit safe vars.
    """
    import os

    started = time.monotonic()
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **spec.env}
    try:
        completed = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            spec.command,
            cwd=str(spec.workdir),
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return ContainerResult(
            exit_code=None, stdout=stdout, stderr=stderr, duration_seconds=duration, timed_out=True
        )
    duration = time.monotonic() - started
    return ContainerResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=duration,
        timed_out=False,
    )


def run_container(spec: ExecutionSpec, *, name: str) -> ContainerResult:
    """Run in Docker with timeout + guaranteed cleanup (`docker rm -f` on timeout)."""
    if not docker_available():
        raise ConfigurationError("docker is not available")
    args = docker_args(spec, name=name)
    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            args, capture_output=True, text=True, timeout=spec.timeout_seconds
        )
    except subprocess.TimeoutExpired as exc:
        subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [  # noqa: S607 - intentional PATH lookup of explicit tool
                "docker",
                "rm",
                "-f",
                name,
            ],
            capture_output=True,
        )
        duration = time.monotonic() - started
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return ContainerResult(
            exit_code=None, stdout=stdout, stderr=stderr, duration_seconds=duration, timed_out=True
        )
    duration = time.monotonic() - started
    # Defensive cleanup (with --rm this is usually a no-op).
    if completed.returncode != 0:
        subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [  # noqa: S607 - intentional PATH lookup of explicit tool
                "docker",
                "rm",
                "-f",
                name,
            ],
            capture_output=True,
        )
    return ContainerResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=duration,
        timed_out=False,
    )


def build_image(*, dockerfile: Path, context: Path, tag: str) -> str:
    """Build an image; return the tag (digest recorded by caller when available)."""
    if not docker_available():
        raise ConfigurationError("docker is not available")
    result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
        [  # noqa: S607 - intentional PATH lookup of explicit tool
            "docker",
            "build",
            "-f",
            str(dockerfile),
            "-t",
            tag,
            str(context),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise ConfigurationError(f"docker build failed: {result.stderr.strip()[-2000:]}")
    return tag
