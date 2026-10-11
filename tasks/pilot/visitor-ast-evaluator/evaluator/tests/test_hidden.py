"""Hidden acceptance tests for AST Expression Evaluator."""

import pytest
from ast_evaluator import evaluate_expression  # ty: ignore[unresolved-import]


def test_complex_arithmetic():
    res = evaluate_expression("3 + 4 * 2 / (1 - 5) ** 2")
    # 3 + 8 / (-4)^2 = 3 + 8 / 16 = 3.5
    assert abs(res - 3.5) < 1e-6


def test_variables_substitution():
    res = evaluate_expression("x * 2 + y", variables={"x": 5.0, "y": 3.0})
    assert res == 13.0

    with pytest.raises(NameError):
        evaluate_expression("unknown + 1", variables={})


def test_disallow_unsafe_nodes():
    with pytest.raises(ValueError):
        evaluate_expression("__import__('os').system('ls')")
