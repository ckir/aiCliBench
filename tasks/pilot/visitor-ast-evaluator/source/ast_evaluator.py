"""AST Expression Evaluator."""

import ast
from typing import Any


class ExpressionEvaluator(ast.NodeVisitor):
    def __init__(self, variables: dict[str, float] | None = None) -> None:
        self.variables = variables or {}

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")


def evaluate_expression(expr: str, variables: dict[str, float] | None = None) -> float:
    # Stub
    return 0.0
