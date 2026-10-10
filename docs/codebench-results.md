# Interpreting CodeBench results

The tool compares full CLI systems (CLI + configured model + harness + tools).
It does not isolate model quality unless harness/tools are held constant —
reports state this explicitly and flag unknown model identity.

Primary metrics (never collapsed to one opaque number):

- Correctness: `pass_rate = acceptance_passes / eligible_evaluations`.
  Evaluation errors are excluded from the denominator and shown separately.
  Always read numerators/denominators, not just percentages.
- `paired_win_rate`: share of valid pairs where only one agent passes; ties
  (`both pass`, `neither passes`) and `invalid` pairs shown separately.
- Runtime: median + IQR over successful runs only. Timeouts reported as counts
  (optionally capped elapsed shown with the cap stated), never averaged as
  completions.
- Cost: provider-reported cost only; missing telemetry is `not available`,
  never invented. `cost_per_success` uses the known-cost cohort with coverage
  (`known/total`) labeled. Subscription plans without telemetry show
  `not available` (or a user estimate labeled as such).
- Quality gates (acceptance, build, lint, typecheck, regression) reported
  separately. Source similarity to a reference patch is never graded.

Cautions:

- Small pilots are not statistically conclusive; do not declare a winner from
  tiny differences. Reports show per-task outcomes, sample counts, and
  warnings for incomplete experiments, invalid pairs, unknown models, or
  uncomparable telemetry.
- A benchmark run can succeed as an experiment while agents fail tasks;
  experiment status vs task success are distinct.
- Invalid tasks, evaluation errors, and missing runs are never counted as
  ordinary failures.
