#!/bin/bash
# Trusted acceptance command. Runs hidden tests only; agent must not see these.
set -euo pipefail
EVAL_DIR="${EVALUATOR_DIR:-/evaluator}"
WORKSPACE_DIR="${WORKSPACE:-/workspace}"
cd "${WORKSPACE_DIR}" 2>/dev/null || true
export PYTHONPATH="${WORKSPACE_DIR}:${PYTHONPATH:-}"
if [ -d "/evaluator/tests" ]; then
  python3 -m pytest /evaluator/tests -v
elif [ -d "${EVAL_DIR}/tests" ]; then
  python3 -m pytest "${EVAL_DIR}/tests" -v
else
  echo "evaluator tests not found" >&2
  exit 2
fi
