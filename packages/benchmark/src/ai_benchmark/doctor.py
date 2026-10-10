"""Environment health checks (§4.1). No paid or state-changing tasks."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_benchmark.config import load_config_file


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[CheckResult, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks],
        }


def _python_check() -> CheckResult:
    version = sys.version.split()[0]
    ok = sys.version_info >= (3, 12)
    return CheckResult(name="python", ok=ok, detail=f"Python {version} (requires >=3.12)")


def _git_check() -> CheckResult:
    if shutil.which("git") is None:
        return CheckResult(name="git", ok=False, detail="git executable not found")
    try:
        result = subprocess.run(
            [  # noqa: S607 - intentional PATH lookup of explicit tool
                "git",
                "--version",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(name="git", ok=False, detail=f"git probe failed: {exc}")
    ok = result.returncode == 0
    return CheckResult(
        name="git", ok=ok, detail=(result.stdout or result.stderr or "").strip()[:200]
    )


def _docker_check() -> CheckResult:
    if shutil.which("docker") is None:
        return CheckResult(name="docker", ok=False, detail="docker CLI not found")
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
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(name="docker", ok=False, detail=f"docker info failed: {exc}")
    if result.returncode != 0:
        return CheckResult(name="docker", ok=False, detail="docker daemon unreachable")
    return CheckResult(
        name="docker", ok=True, detail=f"docker server {result.stdout.strip()[:100]}"
    )


def _cli_check(agent: str, command: str) -> CheckResult:
    if shutil.which(command) is None:
        return CheckResult(name=f"{agent}-cli", ok=False, detail=f"{command!r} not on PATH")
    try:
        version = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [command, "--version"], capture_output=True, text=True, timeout=10
        )
        help_result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
            [command, "--help"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return CheckResult(name=f"{agent}-cli", ok=False, detail=f"probe failed: {exc}")
    version_text = version.stdout or version.stderr or ""
    help_text = (help_result.stdout or "")[:200]
    detail = (version_text + " / " + help_text).strip()[:500]
    ok = help_result.returncode == 0 or version.returncode == 0
    return CheckResult(name=f"{agent}-cli", ok=ok, detail=detail or "present")


def _config_check(config_path: Path | None, data_dir: Path) -> CheckResult:
    try:
        if config_path is not None:
            load_config_file(config_path)
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".writable"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as exc:
        return CheckResult(name="config", ok=False, detail=str(exc)[:500])
    return CheckResult(
        name="config",
        ok=True,
        detail=f"config valid; data dir writable: {data_dir} "
        f"(platform {platform.system()} {platform.machine()})",
    )


def run_doctor(
    *,
    config_path: Path | None = None,
    data_dir: Path | None = None,
    claude_command: str = "claude",
    agy_command: str = "agy",
) -> DoctorReport:
    """Run all health checks without paid or state-changing work."""
    directory = data_dir or Path("runs")
    checks = [
        _python_check(),
        _git_check(),
        _docker_check(),
        _cli_check("claude", claude_command),
        _cli_check("antigravity", agy_command),
        _config_check(config_path, directory),
    ]
    return DoctorReport(checks=tuple(checks))
