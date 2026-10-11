"""CodeBench domain package. No provider SDKs, no MCP transport, no import-time I/O."""

from ai_benchmark.task_verify import TaskVerification, apply_solution, verify_task

__all__: list[str] = ["TaskVerification", "apply_solution", "verify_task"]
