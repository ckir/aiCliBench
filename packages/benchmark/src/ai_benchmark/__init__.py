"""CodeBench domain package. No provider SDKs, no MCP transport, no import-time I/O."""

from ai_benchmark.provenance import (
    ImageCache,
    ImageInfo,
    build_manifest,
    connect_with_migrations,
    environment_digest,
    inspect_image,
    update_experiment_provenance,
)
from ai_benchmark.task_scaffold import scaffold_task
from ai_benchmark.task_verify import TaskVerification, apply_solution, verify_task

__all__: list[str] = [
    "TaskVerification",
    "apply_solution",
    "verify_task",
    "ImageCache",
    "ImageInfo",
    "build_manifest",
    "connect_with_migrations",
    "environment_digest",
    "inspect_image",
    "update_experiment_provenance",
    "scaffold_task",
]
