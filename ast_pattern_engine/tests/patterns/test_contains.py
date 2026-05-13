import ast
from ast_pattern_engine.nodes.basic import Contains, Collect, NodePattern


def test_contains_nested_extraction_and_conflicts():
    # Tree: x = 1 + 2
    node = ast.parse("x = 1 + 2").body[0]

    # Matches because tree contains Add
    pattern1 = Contains([Collect(NodePattern(ast.Add), "op")])
    res1 = pattern1.match_node(node, {})
    assert res1 is not None
    assert "op" in res1
    assert isinstance(res1["op"], ast.Add)

    # Preserves existing bindings
    res2 = pattern1.match_node(node, {"existing": 1})
    assert res2["existing"] == 1
    assert "op" in res2

    # Fails due to duplicate key conflict
    res3 = pattern1.match_node(node, {"op": "conflict"})
    assert res3 is None

    # Fails because tree does not contain Sub
    pattern2 = Contains([NodePattern(ast.Sub)])
    assert pattern2.match_node(node, {}) is None
