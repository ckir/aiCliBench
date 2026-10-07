"""Evaluation framework: deterministic cases plus an optional live suite."""

from ai_evals.cases import EvalCase, EvalResult
from ai_evals.runner import run_eval_case, run_eval_suite, summarize

__all__ = ["EvalCase", "EvalResult", "run_eval_case", "run_eval_suite", "summarize"]
