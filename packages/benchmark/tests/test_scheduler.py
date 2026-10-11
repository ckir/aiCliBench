import contextlib
import json
from pathlib import Path

from ai_benchmark.doctor import run_doctor
from ai_benchmark.fake_agent import FakeAgentAdapter
from ai_benchmark.scheduler import ExperimentRequest, run_experiment
from ai_benchmark.storage import connect, evaluation_for_run, runs_for_experiment
from ai_schemas import BenchmarkConfig


def test_doctor_does_not_start_paid_tasks(tmp_path: Path):
    report = run_doctor(data_dir=tmp_path / "runs")
    names = [c.name for c in report.checks]
    assert "python" in names
    assert "git" in names
    assert "docker" in names
    assert "claude-cli" in names
    assert "config" in names
    # Doctor must not create experiments or require creds.
    assert isinstance(report.ok, bool)


def test_scheduler_paired_reproducible_order(tmp_path: Path):
    from ai_agents.adapter import paired_order

    agents = ["claude", "antigravity"]
    first = paired_order(agents, seed=20261010, pair_key="example-task:1")
    second = paired_order(agents, seed=20261010, pair_key="example-task:1")
    assert first == second


def test_scheduler_full_experiment_with_fakes(tmp_path: Path):
    tasks_root = Path("tasks")
    assert (tasks_root / "pilot" / "example-task" / "task.toml").is_file()
    config = BenchmarkConfig()
    adapters = {
        "claude": FakeAgentAdapter(agent_name="claude", mode="pass"),
        "antigravity": FakeAgentAdapter(agent_name="antigravity", mode="fail"),
    }
    summary = run_experiment(
        config=config,
        tasks_root=tasks_root,
        request=ExperimentRequest(
            suite="pilot",
            task_ids=["example-task"],
            agent_names=["claude", "antigravity"],
            repeat_count=1,
        ),
        adapters=adapters,
        db_path=tmp_path / "codebench.sqlite3",
        runs_dir=tmp_path / "runs",
        experiment_id="exp_test_1",
        use_docker=False,
    )
    assert summary.total_runs == 2
    assert summary.completed == 2
    conn = connect(tmp_path / "codebench.sqlite3")
    runs = runs_for_experiment(conn, "exp_test_1")
    assert len(runs) == 2
    # starting commit pinned and identical for the pair.
    assert runs[0]["starting_commit"] == runs[1]["starting_commit"]
    assert runs[0]["starting_commit"]
    # order_index reflects randomized order (0 and 1 across the pair).
    assert sorted(r["order_index"] for r in runs) == [0, 1]
    assert {r["agent_name"] for r in runs} == {"claude", "antigravity"}
    conn.close()


def test_scheduler_rejects_bad_repeat(tmp_path: Path):
    import pytest

    from ai_core.errors import ConfigurationError

    config = BenchmarkConfig()
    with pytest.raises(ConfigurationError):
        run_experiment(
            config=config,
            tasks_root=Path("tasks"),
            request=ExperimentRequest(
                suite="pilot", task_ids=["example-task"], agent_names=["claude"], repeat_count=0
            ),
            adapters={"claude": FakeAgentAdapter(agent_name="claude")},
            db_path=tmp_path / "db.sqlite3",
            runs_dir=tmp_path / "runs",
            use_docker=False,
        )


def test_scheduler_records_gate_results(tmp_path: Path):
    tasks_root = Path("tasks")
    assert (tasks_root / "pilot" / "example-task" / "task.toml").is_file()
    config = BenchmarkConfig()
    adapters = {
        "claude": FakeAgentAdapter(agent_name="claude", mode="pass"),
        "antigravity": FakeAgentAdapter(agent_name="antigravity", mode="fail"),
    }
    run_experiment(
        config=config,
        tasks_root=tasks_root,
        request=ExperimentRequest(
            suite="pilot",
            task_ids=["example-task"],
            agent_names=["claude", "antigravity"],
            repeat_count=1,
        ),
        adapters=adapters,
        db_path=tmp_path / "codebench.sqlite3",
        runs_dir=tmp_path / "runs",
        experiment_id="exp_gates",
        use_docker=False,
    )
    conn = connect(tmp_path / "codebench.sqlite3")
    runs = runs_for_experiment(conn, "exp_gates")
    evals = {r["agent_name"]: evaluation_for_run(conn, r["id"]) for r in runs}
    claude, antigravity = evals["claude"], evals["antigravity"]
    assert claude is not None
    assert antigravity is not None
    assert claude["build_pass"] == 1
    assert claude["acceptance_pass"] == 1
    assert antigravity["build_pass"] == 1
    assert antigravity["acceptance_pass"] == 0
    assert claude["lint_pass"] is None
    assert "gates" in json.loads(claude["output_json"])
    # provenance: manifest file, stored column, per-run environment digest
    manifest = json.loads((tmp_path / "runs" / "exp_gates" / "manifest.json").read_text())
    entry = manifest["tasks"]["example-task"]
    assert len(entry["commit"]) == 40
    assert entry["instruction_sha256"]
    assert entry["evaluator_digest"]
    assert entry["environment_digest"]
    stored = conn.execute(
        "SELECT provenance_json FROM experiments WHERE id = ?", ("exp_gates",)
    ).fetchone()
    assert json.loads(stored[0])["tasks"]["example-task"] == entry
    assert all(r["environment_digest"] == entry["environment_digest"] for r in runs)


def test_manifest_records_image_id_in_docker_mode(tmp_path: Path, monkeypatch):
    from ai_benchmark import scheduler
    from ai_benchmark.provenance import ImageInfo

    monkeypatch.setattr(
        scheduler, "inspect_image", lambda tag: ImageInfo(image_id="sha256:abc", size_bytes=1)
    )
    # use_docker=None would auto-detect; force the manifest path via a stub
    monkeypatch.setattr("ai_benchmark.docker_runner.docker_available", lambda: True)

    def _stop(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(scheduler, "_run_once", _stop)
    with contextlib.suppress(KeyboardInterrupt):
        run_experiment(
            config=BenchmarkConfig(),
            tasks_root=Path("tasks"),
            request=ExperimentRequest(
                suite="pilot",
                task_ids=["example-task"],
                agent_names=["claude"],
                repeat_count=1,
            ),
            adapters={"claude": FakeAgentAdapter(agent_name="claude", mode="pass")},
            db_path=tmp_path / "c.sqlite3",
            runs_dir=tmp_path / "runs",
            experiment_id="exp_img",
            use_docker=True,
        )
    manifest = json.loads((tmp_path / "runs" / "exp_img" / "manifest.json").read_text())
    assert manifest["tasks"]["example-task"]["image_id"] == "sha256:abc"
