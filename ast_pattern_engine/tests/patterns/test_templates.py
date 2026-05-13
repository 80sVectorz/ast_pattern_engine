import ast
from ast_pattern_engine.nodes.basic import Bind, NodePattern
from ast_pattern_engine.templates import match_in_expr, match_call, match_assign


def test_match_in_expr():
    node = ast.parse("foo()").body[0]
    assert isinstance(node, ast.Expr)

    pattern = match_in_expr(NodePattern(ast.Call))
    res = pattern.match_node(node, {})
    assert res is not None

    fail_node = ast.parse("x = 1").body[0]
    assert pattern.match_node(fail_node, {}) is None


def test_match_call():
    node = ast.parse("foo(1)").body[0].value
    assert isinstance(node, ast.Call)

    pattern = match_call("foo", args=Bind("args"))
    res = pattern.match_node(node, {})
    assert res is not None
    assert "args" in res
    assert len(res["args"]) == 1

    # Fails on different name
    pattern_fail = match_call("bar")
    assert pattern_fail.match_node(node, {}) is None


def test_match_assign():
    node = ast.parse("x = 1").body[0]
    assert isinstance(node, ast.Assign)

    pattern1 = match_assign(target_name="x", value=Bind("val"))
    res1 = pattern1.match_node(node, {})
    assert res1 is not None
    assert "val" in res1

    pattern2 = match_assign(target_name="y")
    assert pattern2.match_node(node, {}) is None
