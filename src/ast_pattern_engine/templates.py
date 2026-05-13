import ast
from typing import Any
from .core import Pattern
from .nodes.basic import NodePattern, Filter
from .nodes.sequences import PatternGroup


def match_in_expr(pattern: Pattern) -> NodePattern:
    """Matches an expression statement containing the given pattern.

    Equivalent to matching an ast.Expr whose `value` is the pattern.

    Args:
        pattern: The pattern to match inside the expression.
    """
    return NodePattern(ast.Expr, value=pattern)


def match_call(func_name: str, **kwargs: Any) -> NodePattern:
    """Matches a function call to a specific function name.

    This matches an ast.Call where the `func` is an ast.Name with the given `id`.
    Any additional kwargs are passed to the ast.Call NodePattern (e.g., args, keywords).

    Args:
        func_name: The name of the function to match.
        **kwargs: Additional constraints to pass to the ast.Call NodePattern.
    """
    return NodePattern(
        ast.Call,
        func=NodePattern(ast.Name, id=Filter(lambda n: n == func_name)),
        **kwargs,
    )


def match_assign(
    target_name: str | None = None, value: Pattern | None = None, **kwargs: Any
) -> NodePattern:
    """Matches an assignment statement.

    If `target_name` is provided, it expects the first target to be an ast.Name with that id.
    If `value` is provided, it expects the assigned value to match the given pattern.

    Args:
        target_name: Optional name of the variable being assigned to.
        value: Optional pattern to match against the assigned value.
        **kwargs: Additional constraints to pass to the ast.Assign NodePattern.
    """
    if target_name is not None:
        kwargs["targets"] = PatternGroup(
            [NodePattern(ast.Name, id=Filter(lambda n: n == target_name))]
        )
    if value is not None:
        kwargs["value"] = value

    return NodePattern(ast.Assign, **kwargs)
