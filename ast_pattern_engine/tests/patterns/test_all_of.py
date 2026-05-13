import ast
from ast_pattern_engine.nodes.basic import AllOf, NodePattern, Filter, Collect


def test_all_of_threading_and_failures():
    node = ast.parse("1").body[0].value

    # Both match
    pattern1 = AllOf([NodePattern(ast.Constant), Filter(lambda x: x.value == 1)])
    assert pattern1.match_node(node, {"existing": 1}) == {"existing": 1}

    # Second fails
    pattern2 = AllOf([NodePattern(ast.Constant), Filter(lambda x: x.value == 2)])
    assert pattern2.match_node(node, {}) is None

    # First fails
    pattern3 = AllOf([NodePattern(ast.Name), Filter(lambda x: x.value == 1)])
    assert pattern3.match_node(node, {}) is None

    # Check that bindings thread through
    pattern4 = AllOf(
        [Collect(NodePattern(ast.Constant), "c"), Filter(lambda x: x.value == 1)]
    )
    res4 = pattern4.match_node(node, {})
    assert "c" in res4
    assert isinstance(res4["c"], ast.Constant)
