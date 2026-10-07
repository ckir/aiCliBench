# ai-evals

Evaluation infrastructure: deterministic cases, fake-model runner, reporting.

- `EvalCase`: input + rubric (`expected_contains`, `expected_tool`).
- `EvalResult`: case/input, expectation, model/provider, config, result, pass/fail,
  and reproduction metadata.
- PR CI runs only deterministic evals (`pytest -m eval`); live-provider evals are
  scheduled separately and never require credentials in PRs.
