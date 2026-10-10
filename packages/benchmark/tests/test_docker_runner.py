from pathlib import Path

import pytest

from ai_benchmark.docker_runner import (
    ExecutionSpec,
    Mount,
    docker_args,
    docker_available,
    run_local,
)
from ai_core.errors import ConfigurationError


def test_run_local_success_and_timeout(tmp_path: Path):
    ok = run_local(ExecutionSpec(command=["echo", "hi"], workdir=tmp_path, timeout_seconds=10))
    assert ok.exit_code == 0
    assert "hi" in ok.stdout
    assert ok.timed_out is False

    slow = run_local(
        ExecutionSpec(
            command=["python3", "-c", "import time; time.sleep(5)"],
            workdir=tmp_path,
            timeout_seconds=0.3,
        )
    )
    assert slow.timed_out is True
    assert slow.exit_code is None


def test_docker_args_hardened(tmp_path: Path):
    spec = ExecutionSpec(
        command=["bash", "/evaluator/run_tests.sh"],
        workdir=tmp_path,
        timeout_seconds=60,
        mounts=(Mount(source=tmp_path, target="/workspace", read_only=False),),
    )
    args = docker_args(spec, name="cb-test")
    joined = " ".join(args)
    assert "--cap-drop ALL" in joined
    assert "no-new-privileges" in joined
    assert "--network none" in joined
    assert "--read-only" in joined
    assert "--rm" in joined
    assert "docker.sock" not in joined


def test_docker_args_refuses_socket(tmp_path: Path):
    spec = ExecutionSpec(
        command=["echo", "hi"],
        workdir=tmp_path,
        timeout_seconds=5,
        mounts=(Mount(source=Path("/var/run/docker.sock"), target="/sock", read_only=True),),
    )
    with pytest.raises(ConfigurationError):
        docker_args(spec, name="cb-bad")


def test_docker_available_returns_bool():
    assert isinstance(docker_available(), bool)
