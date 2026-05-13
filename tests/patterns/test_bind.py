import ast
from ast_pattern_engine.nodes.basic import Bind, NodePattern
from ast_pattern_engine.nodes.sequences import Repetition
from ast_pattern_engine.engine import _match_patterns


def test_bind_matches_and_captures():
    node = ast.parse("1").body[0].value

    # Bind single node
    pattern1 = Bind("my_bind")
    assert pattern1.match_node(node, {}) == {"my_bind": node}

    # Bind fails if duplicate key and not forced list
    assert pattern1.match_node(node, {"my_bind": "existing"}) is None

    # Bind inside repetition creates a list
    rep_pattern = Repetition(Bind("my_items"))
    nodes = [node, node]
    res = _match_patterns([rep_pattern], nodes, 0, {})
    assert res
    assert res[0][0]["my_items"] == [node, node]

    # Nested with NodePattern
    pattern2 = NodePattern(ast.Assign, targets=Bind("target"), value=Bind("val"))
    assign_node = ast.parse("x = 1").body[0]
    res2 = pattern2.match_node(assign_node, {})
    assert res2 is not None
    assert "target" in res2
    assert "val" in res2
    assert isinstance(res2["target"], list)  # targets is a list in ast.Assign
    assert isinstance(res2["val"], ast.Constant)
