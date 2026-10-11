"""AST Expression Evaluator."""

import ast
import operator
from collections.abc import Callable
from typing import Any

_BIN_OPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

_UNARY_OPS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class ExpressionEvaluator(ast.NodeVisitor):
    def __init__(self, variables: dict[str, float] | None = None) -> None:
        self.variables = variables or {}

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsupported AST node: {type(node).__name__}")
        return node.value

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id not in self.variables:
            raise NameError(f"Undefined variable: {node.id}")
        return self.variables[node.id]

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported AST node: {type(node.op).__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        return op(left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported AST node: {type(node.op).__name__}")
        return op(self.visit(node.operand))


def evaluate_expression(expr: str, variables: dict[str, float] | None = None) -> float:
    tree = ast.parse(expr, mode="eval")
    return ExpressionEvaluator(variables).visit(tree)
