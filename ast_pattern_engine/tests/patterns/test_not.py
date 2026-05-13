import ast
from ast_pattern_engine.nodes.basic import Not, NodePattern, Collect


def test_not_preserves_bindings_and_swallows_announcements():
    node = ast.parse("1").body[0].value

    # Inner pattern matches -> Not fails
    pattern1 = Not(NodePattern(ast.Constant))
    assert pattern1.match_node(node, {"existing": 1}) is None

    # Inner pattern fails -> Not matches, existing bindings preserved
    pattern2 = Not(NodePattern(ast.Name))
    assert pattern2.match_node(node, {"existing": 1}) == {"existing": 1}

    # Not never produces bindings from its children, even when they
    # contain Collect nodes — because Not only succeeds when the inner
    # pattern *fails*, so no child bindings ever surface.
    pattern3 = Not(Collect(NodePattern(ast.Name), "swallowed"))
    result = pattern3.match_node(node, {})
    assert result == {}  # inner failed -> Not succeeds with no new bindings
    assert "swallowed" not in result
