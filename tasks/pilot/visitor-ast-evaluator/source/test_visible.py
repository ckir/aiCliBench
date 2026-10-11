from ast_evaluator import evaluate_expression


def test_constant():
    assert evaluate_expression("42") == 42.0
