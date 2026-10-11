# Refactor Expression Evaluation into AST NodeVisitor

In `ast_evaluator.py`, refactor arithmetic expression evaluation using Python's standard `ast.NodeVisitor`.

### Requirements:
Implement `evaluate_expression(expr: str, variables: dict[str, float] | None = None) -> float`:
1. Parses `expr` into an AST using standard `ast.parse(expr, mode='eval')`.
2. Evaluates the expression using a custom `ast.NodeVisitor` subclass.
3. Supports:
   - Literals / Numbers (`ast.Constant`)
   - Binary operators: `+` (`ast.Add`), `-` (`ast.Sub`), `*` (`ast.Mult`), `/` (`ast.Div`), `**` (`ast.Pow`), `%` (`ast.Mod`)
   - Unary operators: `+` (`ast.UAdd`), `-` (`ast.USub`)
   - Variable identifiers: `ast.Name` looked up in `variables` dictionary. If variable not found, raises `NameError(f"Undefined variable: {name}")`.
4. Security: Rejects function calls, attribute access, indexing, or arbitrary statement execution with `ValueError("Unsupported AST node")`.
5. Handles division by zero by raising `ZeroDivisionError`.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
