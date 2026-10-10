"""Task discovery, loading, and validation (§7, §11.3). Never runs an agent."""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ai_agents.adapter import sha256_text, wrap_prompt
from ai_benchmark.paths import safe_join
from ai_core.errors import ConfigurationError, ValidationError
from ai_schemas import TaskDefinition
from ai_schemas.codebench import PROMPT_WRAPPER_VERSION


@dataclass(frozen=True, slots=True)
class LoadedTask:
    definition: TaskDefinition
    task_dir: Path
    instruction_text: str
    instruction_sha256: str
    wrapped_prompt: str
    wrapped_sha256: str
    prompt_wrapper_version: str


def _read_toml(path: Path) -> dict[str, object]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigurationError(f"cannot read {path}: {exc}") from exc
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ConfigurationError(f"invalid TOML in {path}: {exc}") from exc


def load_task(task_dir: Path) -> LoadedTask:
    """Load and validate one task directory.

    Raises:
        ConfigurationError: unreadable/metadata invalid.
        ValidationError: path traversal or unsafe content.
    """
    task_toml = task_dir / "task.toml"
    if not task_toml.is_file():
        raise ConfigurationError(f"missing task.toml in {task_dir}")
    data = _read_toml(task_toml)
    try:
        definition = TaskDefinition.model_validate(data)
    except Exception as exc:
        raise ConfigurationError(f"invalid task.toml in {task_dir}: {exc}") from exc

    # Resolve task-relative paths safely.
    instruction_path = safe_join(task_dir, definition.instruction_file)
    dockerfile_path = safe_join(task_dir, definition.dockerfile)
    if not instruction_path.is_file():
        raise ConfigurationError(f"missing instruction file: {instruction_path}")
    if not dockerfile_path.is_file():
        raise ConfigurationError(f"missing Dockerfile: {dockerfile_path}")

    try:
        instruction_text = instruction_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"cannot read {instruction_path}: {exc}") from exc
    instruction_sha = hashlib.sha256(instruction_text.encode()).hexdigest()
    wrapped = wrap_prompt(instruction_text)
    wrapped_sha = sha256_text(wrapped)
    return LoadedTask(
        definition=definition,
        task_dir=task_dir,
        instruction_text=instruction_text,
        instruction_sha256=instruction_sha,
        wrapped_prompt=wrapped,
        wrapped_sha256=wrapped_sha,
        prompt_wrapper_version=PROMPT_WRAPPER_VERSION,
    )


def discover_tasks(tasks_root: Path, suite: str | None = None) -> list[LoadedTask]:
    """Discover tasks under ``tasks_root/<suite>/<task-id>/``."""
    if not tasks_root.is_dir():
        raise ConfigurationError(f"tasks root not found: {tasks_root}")
    suites = [suite] if suite else sorted(p.name for p in tasks_root.iterdir() if p.is_dir())
    out: list[LoadedTask] = []
    for suite_name in suites:
        suite_dir = tasks_root / suite_name
        if not suite_dir.is_dir():
            raise ConfigurationError(f"suite not found: {suite_name}")
        for task_dir in sorted(p for p in suite_dir.iterdir() if p.is_dir()):
            loaded = load_task(task_dir)
            if loaded.definition.suite != suite_name:
                raise ConfigurationError(
                    f"task {loaded.definition.id} suite mismatch: "
                    f"{loaded.definition.suite!r} vs directory {suite_name!r}"
                )
            out.append(loaded)
    return out


@dataclass(frozen=True, slots=True)
class TaskValidation:
    task_id: str
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def resolve_repository(task_dir: Path, repository: str) -> str:
    """Resolve a task's repository to a cloneable location.

    Task-relative paths (e.g. ``"repo"``) resolve inside *task_dir*;
    URLs and absolute paths pass through unchanged.
    """
    if repository.startswith(("file://", "http://", "https://", "git@", "ssh://")):
        return repository
    candidate = Path(repository)
    if candidate.is_absolute():
        return repository
    return str((task_dir / repository).resolve())


def validate_task(
    task_dir: Path, *, check_repo: bool = True, check_docker: bool = False
) -> TaskValidation:
    """Validate a task without running an agent (§11.3).

    Checks: metadata, paths safe, commit exists (via git ls-remote when
    repository is local or reachable), Dockerfile present, evaluator command
    present, timeout/resource settings sane.
    """
    errors: list[str] = []
    warnings: list[str] = []
    try:
        loaded = load_task(task_dir)
    except (ConfigurationError, ValidationError) as exc:
        return TaskValidation(task_id=task_dir.name, ok=False, errors=(str(exc),), warnings=())
    definition = loaded.definition
    task_id = definition.id

    # Evaluator command must be non-empty (schema already enforces) and
    # evaluator dir should exist when it references /evaluator.
    evaluator_dir = task_dir / "evaluator"
    if not evaluator_dir.is_dir():
        warnings.append("evaluator/ directory missing; evaluator_command must still be valid")

    # Hidden tests must not be referenced by the visible instruction.
    lowered = loaded.instruction_text.lower()
    for hint in ("hidden", "expected patch", "reference solution"):
        if hint in lowered:
            warnings.append(f"instruction mentions {hint!r}; ensure no hidden assertions leak")

    # Commit existence: local paths (including task-relative) or file:// without network.
    if check_repo:
        repo = definition.repository
        repo_path: str | None = None
        if repo.startswith("file://"):
            repo_path = repo[7:]
        elif repo.startswith(("http://", "https://", "git@", "ssh://")):
            repo_path = None  # remote: skip offline check
        else:
            candidate = Path(repo)
            if not candidate.is_absolute():
                candidate = task_dir / repo
            if candidate.exists():
                repo_path = str(candidate)
        if repo_path is not None:
            result = subprocess.run(  # noqa: S603 - fixed arg list, no shell
                [  # noqa: S607 - intentional PATH lookup of explicit tool
                    "git",
                    "cat-file",
                    "-e",
                    f"{definition.commit}^{{commit}}",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                errors.append(f"commit {definition.commit} not found in {repo}")

    if check_docker:
        dockerfile = task_dir / definition.dockerfile
        if not dockerfile.is_file():
            errors.append(f"Dockerfile missing: {dockerfile}")

    ok = not errors
    return TaskValidation(task_id=task_id, ok=ok, errors=tuple(errors), warnings=tuple(warnings))
