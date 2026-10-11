# Interpreting CodeBench results

The tool compares full CLI systems (CLI + configured model + harness + tools).
It does not isolate model quality unless harness/tools are held constant —
reports state this explicitly and flag unknown model identity.

Primary metrics (never collapsed to one opaque number):

- Correctness: `pass_rate = acceptance_passes / eligible_evaluations`.
  Evaluation errors are excluded from the denominator and shown separately.
  Always read numerators/denominators, not just percentages.
  95% Wilson confidence intervals are shown for pass rates.
- Paired outcomes: `a_wins`, `b_wins`, `both_pass`, `neither_pass`, `invalid`.
  Decisive pairs = `a_wins + b_wins`. Exact sign-test p-value and paired
  bootstrap 95% CI for delta(A-B) are reported when decisive pairs exist.
- Runtime: median + IQR over successful runs only. Timeouts reported as counts
  (optionally capped elapsed shown with the cap stated), never averaged as
  completions.
- Cost: provider-reported cost only; missing telemetry is `not available`,
  never invented. `cost_per_success` uses the known-cost cohort with coverage
  (`known/total`) labeled. Subscription plans without telemetry show
  `not available` (or a user estimate labeled as such).
- Quality gates (acceptance, build, lint, typecheck, regression) reported
  separately with `pass/total` counts. Source similarity to a reference patch
  is never graded.

Statistical confidence:

- 95% Wilson score intervals for per-agent pass rates.
- Exact two-sided sign test p-value for paired wins.
- Paired bootstrap (2000 resamples, fixed seed 20261010) 95% CI for delta(A-B)
  pass rate difference. Reported as `n/a` when fewer than 10 decisive pairs.

Cautions:

- Small pilots are not statistically conclusive; do not declare a winner from
  tiny differences. Reports show per-task outcomes, sample counts, and
  warnings for incomplete experiments, invalid pairs, unknown models, or
  uncomparable telemetry.
- A benchmark run can succeed as an experiment while agents fail tasks;
  experiment status vs task success are distinct.
- Invalid tasks, evaluation errors, and missing runs are never counted as
  ordinary failures.